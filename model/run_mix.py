"""Run mix scenarios, verify every solution, write outputs and charts."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
import mix_lp as M

OUT = M.OUT
SCEN = {
    "Base": {},
    "Strict CO2 (0.8 Gt)": dict(co2_cap=800),
    "Relaxed CO2 (1.7 Gt)": dict(co2_cap=1700),
    "Nuclear Mission (100 GW)": dict(nuclear_floor=100),
    "Nuclear delay (<=50 GW)": dict(nuclear_cap=50),
    "Transmission x2 only": dict(tx_mult=2.0),
    "Transmission x5": dict(tx_mult=5.0),
    "Storage cost +50%": dict(storage_cost_mult=1.5),
    "Solar cost +30%": dict(solar_cost_mult=1.3),
    "Faster RE build (+25%)": dict(solar_cap=1279*1.25, wind_cap=375*1.25),
    "Slower RE build (-25%)": dict(solar_cap=1279*0.75, wind_cap=375*0.75),
    "Demand P10": dict(demand="P10"),
    "Demand P90": dict(demand="P90"),
    "Demand P90 + build caps x1.23": dict(demand="P90", solar_cap=1279*1.23, wind_cap=375*1.23, hydro_cap=111*1.1),
}


def verify(o, tol=1e-3):
    """Independent re-checks on the solved numbers (not the solver's own status)."""
    chk = []
    G, C = o["gen"], o["cap"]; GS, STO, FS, H2 = o["gen_slices"], o["storage"], o["flow_slices"], o["h2_slices"]
    p = o["params"]
    # 1 energy balance in every region x slice
    worst = np.inf
    for r in M.REG:
        for (s_, p_) in M.SL:
            gen = GS.query("region==@r and season==@s_ and period==@p_").twh.sum()
            st = STO.query("region==@r and season==@s_ and period==@p_")
            imp = FS.query("to==@r and season==@s_ and period==@p_").twh.sum() * (1 - M.A.transfer_loss)
            exp = FS.query("`from`==@r and season==@s_ and period==@p_").twh.sum()
            bh = M.BHUTAN_TWH * M.HYD_S[s_] * M.PER[p_] / 24 if r == "Eastern" else 0
            dem = o["grid"][r] * M.HRS[(s_, p_)] / 8760 * M.DEM_S[s_] * M.DEM_P[p_]
            h2 = H2.query("region==@r and season==@s_ and period==@p_").twh.sum()
            slack = gen + st.discharge_twh.sum() + imp - exp + bh - dem - st.charge_twh.sum() - h2 + 0
            worst = min(worst, slack)
    chk.append(("Energy balance met in all 60 region-slices (min slack, TWh)", worst >= -tol, round(worst, 4)))
    # 2 national energy accounting
    tot_gen = G.sum().sum(); losses_tx = FS.twh.sum() * M.A.transfer_loss
    sto_loss = (STO.charge_twh - STO.discharge_twh).sum()
    dem = o["demand"].sum(); surplus = tot_gen + M.BHUTAN_TWH - losses_tx - sto_loss - dem + o["unserved"]
    chk.append(("Unserved energy (TWh)", o["unserved"] < 1e-3, round(o["unserved"], 2)))
    chk.append(("National: gen + Bhutan - losses - demand >= 0 (TWh curtailed/spilled)", surplus >= -tol, round(surplus, 1)))
    # 3 annual capacity factors physically possible
    cf = G.sum() / (C.sum() * 8.76)
    lim = {"coal": .85, "gas": .90, "nuclear": .80, "hydro": .45, "solar": .22, "wind": .32}
    chk.append(("National capacity factors within physical limits", all(cf[s] <= lim[s] + tol for s in M.SRC),
                cf.round(3).to_dict()))
    # 4 resource and policy caps
    ok = (C.solar <= M.rg.solar_max_gw + tol).all() and (C.wind <= M.rg.wind_gw + tol).all() \
        and C.solar.sum() <= p["solar_cap"] + tol and C.wind.sum() <= p["wind_cap"] + tol \
        and C.hydro.sum() <= p["hydro_cap"] + tol and C.nuclear.sum() <= p["nuclear_cap"] + tol \
        and (o["psp"] <= M.PSP_MAX + tol).all()
    chk.append(("Resource potentials & build caps respected", bool(ok), ""))
    # 5 committed fleet retained
    ok = all(C.loc[r, s] >= v - tol for (r, s), v in o["committed"].items())
    chk.append(("Committed fleet retained (coal/gas/hydro/nuclear)", ok, round(C.coal.sum(), 1)))
    # 6 CO2
    co2 = 0.96 * G.coal.sum() + 0.40 * G.gas.sum()
    chk.append(("CO2 recomputed <= cap + reported overshoot (Mt)", co2 <= p["co2_cap"] + o["co2_excess"] + 0.1, round(co2)))
    # 7 firm capacity
    fail = []
    for r in M.REG:
        firm = sum(M.CC[s] * C.loc[r, s] for s in M.SRC) + 0.85 * o["bess"][r] + 0.95 * o["psp"][r]
        fail.append(firm / (o["peak"][r] * 1.15))
    chk.append(("Firm capacity / (peak x1.15) by region (<1 means relies on firm imports)", True, [round(x, 2) for x in fail]))
    nat_firm = sum(M.CC[s] * C[s].sum() for s in M.SRC) + 0.85 * o["bess"].sum() + 0.95 * o["psp"].sum()
    chk.append(("National firm capacity >= national peak x1.15", nat_firm >= o["peak"].sum() * 1.15 - tol,
                f"{nat_firm:.0f} vs {o['peak'].sum() * 1.15:.0f} GW"))
    # 8 coal minimum load
    cs = GS[GS.source == "coal"].pivot_table(index=["region", "season"], columns="period", values="twh")
    rate = cs.div(pd.Series(M.PER))
    ok = ((rate.Day >= 0.4 * rate.Evening - tol) & (rate.Night >= 0.4 * rate.Evening - tol)).all()
    chk.append(("Coal minimum-load (40% of evening) respected", bool(ok), ""))
    # 9 storage round-trip
    by = STO.groupby(["region", "season", "kind"])[["charge_twh", "discharge_twh"]].sum()
    eff = {"bess": M.A.bess_eff, "psp": M.A.psp_eff}
    ok = all(abs(row.discharge_twh - eff[k] * row.charge_twh) < 1e-3 for (r, s, k), row in by.iterrows())
    chk.append(("Storage: discharge = efficiency x charge", ok, ""))
    # 10 H2 load fully served
    chk.append(("Electrolyser energy delivered = H2 demand", abs(H2.twh.sum() - o["h2"].sum()) < 1e-3,
                round(H2.twh.sum(), 1)))
    # 11 corridor limits
    worst = 0
    for (a, b), gw in M.CORR.items():
        for t in M.SL:
            x = FS.query("((`from`==@a and to==@b) or (`from`==@b and to==@a)) and season==@t[0] and period==@t[1]").twh.sum()
            worst = max(worst, x / (gw * p["tx_mult"] * M.HRS[t] / 1000 * 0.9))
    chk.append(("Corridor flows <= limit (max utilisation)", worst <= 1 + tol, round(worst, 3)))
    return pd.DataFrame(chk, columns=["check", "pass", "detail"])


def main():
    rows, results = [], {}
    for name, kw in SCEN.items():
        o = M.solve(label=name, **kw); results[name] = o
        rows.append(M.summarise(o))
        if o["status"] == "Optimal":
            v = verify(o)
            if not v["pass"].all():
                print(f"!! {name} failed:\n", v[~v["pass"]])
            if name == "Base":
                v.to_csv(OUT / "mix_verification_base.csv", index=False); print(v.to_string())
    S = pd.DataFrame(rows); S.to_csv(OUT / "mix_scenarios_2047.csv", index=False)
    pd.set_option("display.width", 250); print("\n", S.to_string(index=False))

    b = results["Base"]
    G = b["gen"]; C = b["cap"].assign(bess=b["bess"], psp=b["psp"])
    G.assign(total=G.sum(axis=1)).round(1).to_csv(OUT / "mix_base_generation_twh.csv")
    (G.div(G.sum(axis=1), axis=0) * 100).round(1).to_csv(OUT / "mix_base_share_pct.csv")
    C.round(1).to_csv(OUT / "mix_base_capacity_gw.csv")
    b["gen_slices"].to_csv(OUT / "mix_base_slices.csv", index=False)
    b["storage"].to_csv(OUT / "mix_base_storage.csv", index=False)
    b["flow_slices"].to_csv(OUT / "mix_base_flows.csv", index=False)
    # balance by region: own gen vs demand
    bal = pd.DataFrame({"generation_twh": G.sum(axis=1), "demand_twh": b["demand"]})
    bal["net_export_twh"] = bal.generation_twh - bal.demand_twh
    bal.round(1).to_csv(OUT / "mix_base_regional_balance.csv"); print("\n", bal.round(0).to_string())

    # ---- charts
    col = {"coal": "#4a4a4a", "gas": "#9c7a3c", "nuclear": "#7b5ea7", "hydro": "#2f7fb5", "solar": "#e8b931", "wind": "#5bb59a"}
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.2))
    left = np.zeros(len(M.REG))
    for s in M.SRC:
        ax[0].barh(M.REG, G[s], left=left, color=col[s], label=s.capitalize()); left += G[s].values
    ax[0].invert_yaxis(); ax[0].set_xlabel("TWh generated, FY2046-47"); ax[0].set_title("Base mix by region")
    ax[0].legend(ncol=3, fontsize=8, frameon=False)
    ok = S[S.status.isna()] if "status" in S else S
    ok = S.dropna(subset=["total_gen_twh"])
    left = np.zeros(len(ok))
    for s in M.SRC:
        ax[1].barh(ok.scenario, ok[f"{s}_%"], left=left, color=col[s]); left += ok[f"{s}_%"].values
    ax[1].invert_yaxis(); ax[1].set_xlabel("% of national generation"); ax[1].set_title("National mix across scenarios")
    plt.tight_layout(); plt.savefig(OUT / "mix_regional_and_scenarios.png", dpi=150)

    # dispatch by slice (national)
    GS = b["gen_slices"].groupby(["season", "period", "source"]).twh.sum().unstack()
    GS = GS.reindex([(s, p) for s in M.SEAS for p in M.PER])
    hrs = pd.Series({t: M.HRS[t] for t in M.SL})
    avg_gw = GS.div(hrs, axis=0) * 1000
    fig, ax = plt.subplots(figsize=(13, 4.8)); bottom = np.zeros(len(avg_gw))
    lbl = [f"{s[:3]}-{p[:3]}" for s, p in avg_gw.index]
    for s in M.SRC:
        ax.bar(lbl, avg_gw[s], bottom=bottom, color=col[s], label=s.capitalize()); bottom += avg_gw[s].values
    sto = b["storage"].groupby(["season", "period"])[["discharge_twh"]].sum().reindex(avg_gw.index)
    ax.bar(lbl, sto.discharge_twh.values / hrs.values * 1000, bottom=bottom, color="#d0587e", label="Storage discharge")
    dem = np.array([b["grid"].sum() * M.DEM_S[s_] * M.DEM_P[p_] / 8.76 for s_, p_ in avg_gw.index])
    chg = b["storage"].groupby(["season", "period"]).charge_twh.sum().reindex(avg_gw.index).values / hrs.values * 1000
    h2l = b["h2_slices"].groupby(["season", "period"]).twh.sum().reindex(avg_gw.index).values / hrs.values * 1000
    ax.plot(lbl, dem, "k_", ms=28, mew=2.5, label="Grid demand")
    ax.plot(lbl, dem + chg + h2l, "_", color="#d0587e", ms=28, mew=2.5, label="+ storage charging + electrolysers")
    ax.set_ylim(0, max(bottom.max(), (dem + chg + h2l).max()) * 1.12)
    ax.set_ylabel("Average GW in slice"); ax.set_title("Base 2047: how each season-period is supplied (national)")
    ax.legend(ncol=5, fontsize=8, frameon=False, loc="upper left"); plt.xticks(rotation=45)
    plt.tight_layout(); plt.savefig(OUT / "mix_dispatch_slices.png", dpi=150)
    return S, results


if __name__ == "__main__":
    main()
