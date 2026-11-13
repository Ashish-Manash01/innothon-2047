"""Regional generation-mix optimisation for India, FY2046-47 (linear programme, HiGHS solver).

Choice variables (per region r): new capacity of coal, gas, nuclear, hydro, solar, wind, 4-h batteries (BESS) and
8-h pumped storage (PSP); generation in 12 representative time slices (4 seasons x day/evening/night); storage charge
/discharge; inter-regional flows per slice. Objective: minimise annual system cost (fixed + variable + wheeling).

Constraints
  1  Energy balance in every region x slice (generation + storage discharge + imports(1-loss) - exports
     >= demand_slice + storage charge + flexible electrolyser load)
  2  Resource limits: solar (NISE), wind (NIWE 150 m), hydro (CEA exploitable), PSP (CEA 267 GW), nuclear (sites + 100 GW mission)
  3  Committed fleet kept: coal operating after 40-year retirements + under construction + contracted; existing gas;
     hydro & nuclear operating + under construction (+ sanctioned nuclear); PSP operating + UC
  4  Firm capacity >= peak x 1.15 (capacity credits; storage credited; firm imports up to corridor GW)
  5  Coal minimum load: coal output in each slice >= 40% of its own output rate in the evening (CEA flexibility norm)
  6  Nuclear runs flat (baseload); hydro limited to its seasonal water budget
  7  Corridors: |flow| in each slice <= corridor GW x hours x 0.9
  8  Annual CO2 (coal 0.96, gas 0.40 t/MWh) <= cap
Metric = energy generated (TWh).
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pulp

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
A = pd.read_csv(D / "mix_assumptions.csv").set_index("item").value.astype(float)
H = 8.76

# ---------------------------------------------------------------- time slices
SEAS = {"Summer": 92, "Monsoon": 122, "PostMonsoon": 61, "Winter": 90}         # Mar-May, Jun-Sep, Oct-Nov, Dec-Feb
PER = {"Day": 8, "Evening": 6, "Night": 10}                                    # 08-16, 16-22, 22-08
SL = [(s, p) for s in SEAS for p in PER]
HRS = {(s, p): SEAS[s] * PER[p] for s, p in SL}                                # hours per slice (sum 8760)


def _norm(rel, weight):
    w = np.array([weight[k] for k in rel], float); v = np.array([rel[k] for k in rel], float)
    return {k: x / (v @ w / w.sum()) for k, x in rel.items()}


DEM_S = _norm({"Summer": 1.08, "Monsoon": 1.00, "PostMonsoon": 0.98, "Winter": 0.94}, SEAS)
DEM_P = _norm({"Day": 1.05, "Evening": 1.08, "Night": 0.90}, PER)
SOL_S = _norm({"Summer": 1.12, "Monsoon": 0.82, "PostMonsoon": 1.05, "Winter": 1.02}, SEAS)
SOL_P = {"Day": 0.92 * 24 / 8, "Evening": 0.08 * 24 / 6, "Night": 0.0}
WIN_S = _norm({"Summer": 0.95, "Monsoon": 1.75, "PostMonsoon": 0.55, "Winter": 0.55}, SEAS)
WIN_P = _norm({"Day": 0.90, "Evening": 1.10, "Night": 1.05}, PER)
HYD_S = {"Summer": 0.22, "Monsoon": 0.45, "PostMonsoon": 0.17, "Winter": 0.16}

# ---------------------------------------------------------------- regional data
res = pd.read_csv(D / "state_resources.csv")
rg = res.groupby("cea_region").agg(solar_gwp=("solar_potential_gwp", "sum"), wind_gw=("wind150_potential_gw", "sum"),
                                   hydro_max=("hydro_exploitable_mw", "sum"), hydro_op=("hydro_operating_mw", "sum"),
                                   hydro_uc=("hydro_under_constr_mw", "sum")).reindex(REG).fillna(0)
rg["solar_max_gw"] = rg.solar_gwp / 1.25
rg["hydro_max_gw"] = rg.hydro_max / 1e3; rg["hydro_min_gw"] = (rg.hydro_op + rg.hydro_uc) / 1e3
nuc = pd.read_csv(D / "nuclear_sites.csv")
nuc_site = nuc.groupby("cea_region").capacity_mw.sum().reindex(REG).fillna(0) / 1e3
nuc_min = nuc[nuc.status.isin(["operating", "under construction", "sanctioned (pre-project)"])] \
    .groupby("cea_region").capacity_mw.sum().reindex(REG).fillna(0) / 1e3
capm = pd.read_csv(D / "region_capacity_mar26.csv", index_col=0).reindex(REG)
COAL_COMMITTED_NAT = A.coal_existing_mar26_gw - A.coal_pre2007_retire_gw + A.coal_under_constr_gw + A.coal_contracted_gw
COAL_MIN = capm.coal / capm.coal.sum() * COAL_COMMITTED_NAT + capm.lignite / capm.lignite.sum() * A.lignite_2047_gw
GAS_MIN = capm.gas / 1e3
psp_share = pd.Series({"Western": 129.72, "Southern": 97.76, "Northern": 50.0, "Eastern": 45.0, "North-Eastern": 22.9})
PSP_MAX = (psp_share / psp_share.sum() * A.psp_potential_gw).reindex(REG)
PSP_MIN = pd.Series({"Western": 12.0, "Southern": 8.0, "Northern": 1.0, "Eastern": 2.3, "North-Eastern": 0.0}).reindex(REG)
PSP_MIN = PSP_MIN * A.psp_existing_uc_gw / PSP_MIN.sum()
CF = pd.DataFrame({
    "hydro": pd.Series({"Northern": 82.67 / 21.67, "Western": 20.28 / 7.39, "Southern": 43.44 / 13.60,
                        "Eastern": 12.54 / 5.99, "North-Eastern": 8.22 / 2.77}) / H,
    "solar": pd.Series({"Northern": 0.22, "Western": 0.21, "Southern": 0.20, "Eastern": 0.18, "North-Eastern": 0.16}),
    "wind": pd.Series({"Northern": 0.30, "Western": 0.32, "Southern": 0.32, "Eastern": 0.25, "North-Eastern": 0.25}),
}, index=REG)
AVAIL = {"coal": 0.85, "gas": 0.90, "nuclear": 0.80}
PITHEAD = {"Eastern", "Western"}
CORR = {("Eastern", "Northern"): 22.53, ("Eastern", "Western"): 22.79, ("Western", "Northern"): 38.32,
        ("Eastern", "Southern"): 7.83, ("Western", "Southern"): 22.32, ("Eastern", "North-Eastern"): 3.55,
        ("North-Eastern", "Northern"): 3.00}
BHUTAN_TWH = 7.8
CC = {"coal": 0.85, "gas": 0.90, "nuclear": 0.85, "hydro": 0.60, "solar": 0.05, "wind": 0.15}


def demand_2047(which="base"):
    r = pd.read_csv(OUT / "v2_regional_2047_base.csv", index_col=0).drop(index="India")
    grid, h2 = r.gen_grid_2047_twh.reindex(REG), r.gen_h2_2047_twh.reindex(REG)
    if which != "base":
        q = pd.read_csv(OUT / "v2_mc_quantiles_2047.csv", index_col=0)
        grid = grid * q.loc["gen_grid_2047", which] / grid.sum(); h2 = h2 * q.loc["gen_h2_2047", which] / h2.sum()
    return grid, h2


def solve(co2_cap=A.co2_cap_base_mt, nuclear_cap=A.nuclear_cap_national_gw, tx_mult=A.tx_multiplier_base,
          demand="base", solar_cost_mult=1.0, storage_cost_mult=1.0, coal_cap=A.coal_cap_national_gw,
          wind_cap=A.wind_cap_2047_gw, solar_cap=A.solar_cap_2047_gw, hydro_cap=A.hydro_cap_2047_gw,
          nuclear_floor=0.0, co2_penalty=20000.0, voll=50.0, label="Base", verbose=False, dem=None, cfg=None):
    """cfg (optional, for pathway years): coal_committed (national GW), nuc_min (Series GW), hydro_min (Series GW),
    psp_min (national GW), solar_min / wind_min (national GW already installed), load_factor, bridge, fixed_cap
    (dict {(region, source): GW} pinned exactly, used for the FY26 backcast), no_new_storage (bool)."""
    cfg = cfg or {}
    grid, h2 = dem if dem is not None else demand_2047(demand)
    grid, h2 = grid.reindex(REG), h2.reindex(REG)
    peak = grid / cfg.get("bridge", 1.06) / (H * cfg.get("load_factor", A.load_factor_2047))
    coal_min = cfg["coal_min"] if "coal_min" in cfg else (COAL_MIN * (cfg["coal_committed"] / COAL_MIN.sum()) if "coal_committed" in cfg else COAL_MIN)
    nmin = cfg.get("nuc_min", nuc_min); hmin = cfg.get("hydro_min", rg.hydro_min_gw)
    pmin = PSP_MIN * (cfg["psp_min"] / PSP_MIN.sum()) if "psp_min" in cfg else PSP_MIN
    m = pulp.LpProblem("mix2047", pulp.LpMinimize)
    V = lambda n: m.add_variable(n, lowBound=0)
    ab = {r: r[:3] for r in REG}
    cap = {(r, s): V(f"cap_{ab[r]}_{s}") for r in REG for s in SRC}
    add = {(r, s): V(f"add_{ab[r]}_{s}") for r in REG for s in SRC}
    bess = {r: V(f"bess_{ab[r]}") for r in REG}; psp = {r: V(f"psp_{ab[r]}") for r in REG}
    g = {(r, s, t): V(f"g_{ab[r]}_{s}_{t[0]}_{t[1]}") for r in REG for s in SRC for t in SL}
    sd = {(r, k, t): V(f"dis_{k}_{ab[r]}_{t[0]}_{t[1]}") for r in REG for k in ("bess", "psp") for t in SL}
    sc = {(r, k, t): V(f"chg_{k}_{ab[r]}_{t[0]}_{t[1]}") for r in REG for k in ("bess", "psp") for t in SL}
    hl = {(r, t): V(f"h2_{ab[r]}_{t[0]}_{t[1]}") for r in REG for t in SL}
    # coal fleet heterogeneity: 3 equal tranches with variable cost offsets (CERC merit-order spread)
    TR = cfg.get("coal_tranches", [-0.6, 0.0, 0.6])
    gc = {(r, k, t): V(f"gc_{ab[r]}_{k}_{t[0]}_{t[1]}") for r in REG for k in range(len(TR)) for t in SL}
    arcs = [(a, b) for (a, b) in CORR] + [(b, a) for (a, b) in CORR]
    f = {(a, b, t): V(f"f_{ab[a]}_{ab[b]}_{t[0]}_{t[1]}") for (a, b) in arcs for t in SL}
    firm = {(a, b): V(f"firm_{ab[a]}_{ab[b]}") for (a, b) in arcs}
    uns = {(r, t): V(f"uns_{ab[r]}_{t[0]}_{t[1]}") for r in REG for t in SL}

    newfix = {"coal": A.coal_fixed, "gas": A.gas_fixed, "nuclear": A.nuclear_fixed, "hydro": A.hydro_fixed,
              "solar": A.solar_fixed * solar_cost_mult, "wind": A.wind_fixed}
    var = lambda r, s: {"coal": A.coal_var_pithead + (0 if r in PITHEAD else A.coal_var_nonpithead_extra),
                        "gas": A.gas_var, "nuclear": A.nuclear_var}.get(s, 0.0)
    committed = {}
    for r in REG:
        committed[(r, "coal")] = coal_min[r]; committed[(r, "gas")] = GAS_MIN[r]
        committed[(r, "nuclear")] = nmin[r]; committed[(r, "hydro")] = hmin[r]
    om_sunk = {"coal": A.coal_sunk_om, "gas": A.gas_sunk_om, "nuclear": 0.6, "hydro": 0.3}
    sunk_cost = float(sum(om_sunk[s] * 1000 * v for (r, s), v in committed.items()))
    obj = (pulp.lpSum(newfix[s] * 1000 * add[(r, s)] for r in REG for s in SRC)
           + pulp.lpSum(var(r, s) * 100 * g[(r, s, t)] for r in REG for s in SRC for t in SL)
           + pulp.lpSum(TR[k] * 100 * gc[(r, k, t)] for r in REG for k in range(len(TR)) for t in SL)
           + pulp.lpSum(storage_cost_mult * (A.bess4h_fixed * 1000 * bess[r] + A.psp_fixed * 1000 * psp[r]) for r in REG)
           + pulp.lpSum(cfg.get("transfer_cost", A.transfer_cost) * 100 * x for x in f.values()))
    pen_uns = pulp.lpSum(voll * 100 * x for x in uns.values())
    m += obj

    for r in REG:
        for s in SRC:
            m += cap[(r, s)] == committed.get((r, s), 0.0) + add[(r, s)]
        m += cap[(r, "solar")] <= rg.solar_max_gw[r]
        m += cap[(r, "wind")] <= rg.wind_gw[r]
        m += cap[(r, "hydro")] <= max(rg.hydro_max_gw[r], hmin[r])
        m += cap[(r, "nuclear")] <= nuc_site[r] + max(nuclear_cap - nuc_site.sum(), 0)
        m += psp[r] <= max(PSP_MAX[r], pmin[r]); m += psp[r] >= pmin[r]
        if cfg.get("no_new_storage"):
            m += psp[r] <= pmin[r]; m += bess[r] <= cfg.get("bess_now", {}).get(r, 0.0)
        for t in SL:
            s_, p_ = t; hrs = HRS[t] / 1000
            m += g[(r, "coal", t)] <= cap[(r, "coal")] * hrs * AVAIL["coal"]
            m += g[(r, "coal", t)] == pulp.lpSum(gc[(r, k, t)] for k in range(len(TR)))
            for k in range(len(TR)):
                m += gc[(r, k, t)] <= cap[(r, "coal")] * (hrs * AVAIL["coal"] / len(TR))
            m += g[(r, "gas", t)] <= cap[(r, "gas")] * hrs * AVAIL["gas"]
            m += g[(r, "nuclear", t)] == cap[(r, "nuclear")] * hrs * AVAIL["nuclear"]
            m += g[(r, "solar", t)] <= cap[(r, "solar")] * hrs * CF.loc[r, "solar"] * SOL_S[s_] * SOL_P[p_]
            m += g[(r, "wind", t)] <= cap[(r, "wind")] * hrs * CF.loc[r, "wind"] * WIN_S[s_] * WIN_P[p_]
            m += g[(r, "hydro", t)] <= cap[(r, "hydro")] * hrs
            if p_ != "Evening":
                m += g[(r, "coal", t)] * (1 / PER[p_]) >= g[(r, "coal", (s_, "Evening"))] * (A.coal_min_load / PER["Evening"])
            m += sd[(r, "bess", t)] <= bess[r] * hrs; m += sc[(r, "bess", t)] <= bess[r] * hrs
            m += sd[(r, "psp", t)] <= psp[r] * hrs; m += sc[(r, "psp", t)] <= psp[r] * hrs
            m += hl[(r, t)] <= 2 * h2[r] * HRS[t] / 8760
            dem = grid[r] * HRS[t] / 8760 * DEM_S[s_] * DEM_P[p_]
            imp = pulp.lpSum(f[(a, b, t)] * (1 - A.transfer_loss) for (a, b) in arcs if b == r)
            exp = pulp.lpSum(f[(a, b, t)] for (a, b) in arcs if a == r)
            bh = BHUTAN_TWH * HYD_S[s_] * PER[p_] / 24 if r == "Eastern" else 0.0
            m += (pulp.lpSum(g[(r, s, t)] for s in SRC) + sd[(r, "bess", t)] + sd[(r, "psp", t)] + imp - exp + bh + uns[(r, t)]
                  >= dem + sc[(r, "bess", t)] + sc[(r, "psp", t)] + hl[(r, t)]), f"bal_{ab[r]}_{s_}_{p_}"
        for s_ in SEAS:
            ts = [(s_, p) for p in PER]
            m += pulp.lpSum(g[(r, "hydro", t)] for t in ts) <= cap[(r, "hydro")] * (H * CF.loc[r, "hydro"] * HYD_S[s_])
            for k, hk, eff in (("bess", A.bess_hours, A.bess_eff), ("psp", A.psp_hours, A.psp_eff)):
                stv = bess[r] if k == "bess" else psp[r]
                m += pulp.lpSum(sd[(r, k, t)] for t in ts) == pulp.lpSum(sc[(r, k, t)] for t in ts) * eff
                m += pulp.lpSum(sd[(r, k, t)] for t in ts) <= stv * (hk * SEAS[s_] / 1000)
        m += pulp.lpSum(hl[(r, t)] for t in SL) == h2[r]
        fin = pulp.lpSum(firm[(a, b)] for (a, b) in arcs if b == r)
        fout = pulp.lpSum(firm[(a, b)] for (a, b) in arcs if a == r)
        m += (pulp.lpSum(CC[s] * cap[(r, s)] for s in SRC) + A.cc_bess * bess[r] + 0.95 * psp[r] + fin - fout
              >= peak[r] * (1 + cfg.get("reserve", A.reserve_margin))), f"firm_{ab[r]}"
    for (a, b), gw in CORR.items():
        for t in SL:
            m += f[(a, b, t)] + f[(b, a, t)] <= gw * tx_mult * HRS[t] / 1000 * 0.9
        m += firm[(a, b)] + firm[(b, a)] <= gw * tx_mult
    m += pulp.lpSum(cap[(r, "coal")] for r in REG) <= max(coal_cap, coal_min.sum())
    if "solar_min" in cfg:
        m += pulp.lpSum(cap[(r, "solar")] for r in REG) >= cfg["solar_min"]
    if "wind_min" in cfg:
        m += pulp.lpSum(cap[(r, "wind")] for r in REG) >= cfg["wind_min"]
    for (r, s_), v in cfg.get("fixed_cap", {}).items():
        m += cap[(r, s_)] == v
    m += pulp.lpSum(cap[(r, "gas")] for r in REG) <= A.gas_cap_national_gw
    m += pulp.lpSum(cap[(r, "nuclear")] for r in REG) <= max(nuclear_cap, float(nmin.sum()))
    m += pulp.lpSum(cap[(r, "nuclear")] for r in REG) >= nuclear_floor
    m += pulp.lpSum(cap[(r, "wind")] for r in REG) <= wind_cap
    m += pulp.lpSum(cap[(r, "solar")] for r in REG) <= solar_cap
    m += pulp.lpSum(cap[(r, "hydro")] for r in REG) <= max(hydro_cap, float(hmin.sum()))
    co2 = pulp.lpSum(0.96 * g[(r, "coal", t)] + 0.40 * g[(r, "gas", t)] for r in REG for t in SL)
    co2_x = V("co2_excess")
    m += co2 <= co2_cap + co2_x, "co2_cap"
    m.setObjective(obj + pen_uns + co2_x * (co2_penalty / 10))

    res_ = m.solve(pulp.HiGHS(msg=verbose))
    st = res_.status.name
    if st != "Optimal":
        return {"label": label, "status": st}
    CONS = {c.name: c for c in m.constraints()}
    gv = lambda x: x.value() or 0.0
    G = pd.DataFrame({s: {r: sum(gv(g[(r, s, t)]) for t in SL) for r in REG} for s in SRC})
    C = pd.DataFrame({s: {r: gv(cap[(r, s)]) for r in REG} for s in SRC})
    GS = pd.DataFrame([{"region": r, "season": t[0], "period": t[1], "source": s, "twh": gv(g[(r, s, t)])}
                       for r in REG for s in SRC for t in SL])
    STO = pd.DataFrame([{"region": r, "season": t[0], "period": t[1], "kind": k,
                         "charge_twh": gv(sc[(r, k, t)]), "discharge_twh": gv(sd[(r, k, t)])}
                        for r in REG for k in ("bess", "psp") for t in SL])
    FLS = pd.DataFrame([{"from": a, "to": b, "season": t[0], "period": t[1], "twh": gv(f[(a, b, t)])} for (a, b) in arcs for t in SL])
    H2L = pd.DataFrame([{"region": r, "season": t[0], "period": t[1], "twh": gv(hl[(r, t)])} for r in REG for t in SL])
    return dict(label=label, status=st, gen=G, cap=C, gen_slices=GS, storage=STO, flow_slices=FLS, h2_slices=H2L,
                bess=pd.Series({r: gv(bess[r]) for r in REG}), psp=pd.Series({r: gv(psp[r]) for r in REG}),
                flows=FLS.groupby(["from", "to"]).twh.sum(), co2=co2.value(),
                cost_cr=pulp.value(obj) + sunk_cost, co2_excess=gv(co2_x), unserved=sum(gv(x) for x in uns.values()), demand=grid + h2, grid=grid, h2=h2,
                peak=peak, co2_dual=CONS["co2_cap"].pi, cons=CONS, committed=committed,
                params=dict(co2_cap=co2_cap, nuclear_cap=nuclear_cap, tx_mult=tx_mult, demand=demand,
                            solar_cost_mult=solar_cost_mult, storage_cost_mult=storage_cost_mult, coal_cap=coal_cap,
                            wind_cap=wind_cap, solar_cap=solar_cap, hydro_cap=hydro_cap, nuclear_floor=nuclear_floor))


def summarise(o):
    if o["status"] != "Optimal":
        return {"scenario": o["label"], "status": o["status"]}
    G = o["gen"]; tot = G.sum().sum(); nat = G.sum() / tot * 100; C = o["cap"].sum()
    return {"scenario": o["label"], "total_gen_twh": round(tot), **{f"{s}_%": round(nat[s], 1) for s in SRC},
            "non_fossil_%": round(100 - nat.coal - nat.gas, 1), "co2_mt": round(o["co2"]),
            **{f"{s}_gw": round(C[s]) for s in SRC}, "bess_gw": round(o["bess"].sum()), "psp_gw": round(o["psp"].sum()),
            "cost_rs_per_kwh": round(o["cost_cr"] / (tot * 100), 2),
            # dual of CO2 cap: Rs crore per Mt -> Rs per tonne = crore*1e7/1e6 = x10
            "co2_shadow_rs_per_t": round(abs(o["co2_dual"]) * 10), "co2_over_cap_mt": round(o["co2_excess"]), "unserved_twh": round(o["unserved"], 1)}


if __name__ == "__main__":
    base = solve(label="Base")
    print("Status:", base["status"])
    G, C = base["gen"], base["cap"]
    pd.set_option("display.width", 200)
    print("\nGeneration 2047 (TWh):\n", G.round(0).assign(total=G.sum(axis=1).round(0)).to_string())
    print("\nRegional own-generation shares (%):\n", (G.div(G.sum(axis=1), axis=0) * 100).round(1).to_string())
    print("\nCapacity (GW):\n", C.round(1).assign(bess=base["bess"].round(1), psp=base["psp"].round(1)).to_string())
    print("\nFlows (TWh):\n", base["flows"][base["flows"] > 0.5].round(0).to_string())
    print("\nSummary:", summarise(base))
