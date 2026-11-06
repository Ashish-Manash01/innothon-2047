"""2026 -> 2047 pathway: solve the regional mix LP at milestone years (FY ending 2030, 2035, 2040, 2047) with
year-specific demand (demand model v1, regionalised), committed fleet, build caps, transmission and CO2 caps.

Anchors (all documented in data/mix_assumptions.csv or below)
  - FY26 actual fleet (CEA 31-03-2026): coal 221.9 + lignite 6.6, gas 20.1, nuclear 8.78, large hydro 51.4,
    solar 150.3, wind 56.1, PSP 7.43 GW.
  - CEA projection for 2035-36: coal+lignite 315, gas 20, nuclear 22, hydro 78, solar 509, wind 155 GW.
  - 2047 caps: solar 1,279, wind 375, hydro 111, nuclear 100 (Nuclear Energy Mission), coal 280 GW.
  - Build caps for 2030/2035/2040 = straight-line between those anchors (FY26 -> FY36 -> FY47).
  - Committed coal: today's fleet + 39.5 GW under construction (by FY30) + 22.9 GW contracted (by FY34),
    minus 60 GW of pre-2007 units retired evenly FY27-FY47 (~2.9 GW/yr).
  - Nuclear minimum: operating + under construction (6.6 GW due by FY30); + sanctioned 8.0 GW from FY35.
  - CO2 cap path (peak-and-decline, consistent with Net Zero 2070): FY30 1,400; FY35 1,450; FY40 1,350; FY47 1,200 Mt.
  - Inter-regional transfer capacity: x1.4 by FY30 (CEA plan ~168 GW by 2032), x1.8 FY35, x2.3 FY40, x3 FY47.
  - Load factor 0.80 (FY26) falling linearly to 0.72 (FY47).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_v1 as dm
import mix_lp as M
from regional import regional

YEARS = [2030, 2035, 2040, 2047]
NOW = dict(solar=150.3, wind=56.1, hydro=51.4, nuclear=8.78, coal=221.9 + 6.6)
C36 = dict(solar=509, wind=155, hydro=78, nuclear=22, coal=315)
C47 = dict(solar=M.A.solar_cap_2047_gw, wind=M.A.wind_cap_2047_gw, hydro=M.A.hydro_cap_2047_gw, nuclear=100, coal=280)


def cap_path(src, y):
    return float(np.interp(y, [2026, 2036, 2047], [NOW[src], C36[src], C47[src]]))


def committed_coal(y):
    uc = M.A.coal_under_constr_gw * min(max((y - 2026) / 4, 0), 1)
    con = M.A.coal_contracted_gw * min(max((y - 2028) / 6, 0), 1)
    ret = M.A.coal_pre2007_retire_gw * min(max((y - 2026) / 21, 0), 1)
    lig = float(np.interp(y, [2026, 2047], [6.6, M.A.lignite_2047_gw]))
    return M.A.coal_existing_mar26_gw + uc + con - ret + lig


def nuc_min(y):
    nuc = M.nuc.copy()
    keep = ["operating"] + (["under construction"] if y >= 2030 else []) + (["sanctioned (pre-project)"] if y >= 2035 else [])
    return nuc[nuc.status.isin(keep)].groupby("cea_region").capacity_mw.sum().reindex(M.REG).fillna(0) / 1e3


def hydro_min(y):
    f = min(max((y - 2026) / 6, 0), 1)       # under-construction hydro commissions by ~FY32
    return (M.rg.hydro_op + f * M.rg.hydro_uc) / 1e3


CO2 = {2030: 1400, 2035: 1450, 2040: 1350, 2047: 1200}
TX = {2030: 1.4, 2035: 1.8, 2040: 2.3, 2047: 3.0}


def run_path(p=None, label="Base", co2=None, years=YEARS):
    p = p or dm.SCEN["Base"]; co2 = co2 or CO2
    reg, nb = regional(p, years)
    out = {}
    for y in years:
        d = reg[reg.fy_end == y].set_index("region")
        lf = float(np.interp(y, [2026, 2047], [0.80, 0.72]))
        cfg = dict(coal_committed=committed_coal(y), nuc_min=nuc_min(y), hydro_min=hydro_min(y),
                   psp_min=M.A.psp_existing_uc_gw if y >= 2030 else 7.43,
                   solar_min=NOW["solar"], wind_min=NOW["wind"], load_factor=lf, bridge=float(nb.loc[y, "bridge"]))
        o = M.solve(co2_cap=co2[y], tx_mult=TX[y], dem=(d.gen_grid_twh, d.gen_h2_twh), cfg=cfg,
                    solar_cap=cap_path("solar", y), wind_cap=cap_path("wind", y), hydro_cap=cap_path("hydro", y),
                    nuclear_cap=cap_path("nuclear", y), coal_cap=cap_path("coal", y), label=f"{label} {y}")
        out[y] = o
    return out


if __name__ == "__main__":
    res = run_path()
    rows, regrows = [], []
    act = pd.read_csv(M.D / "region_generation_fy26.csv", index_col=0)
    a = act[["coal_lignite", "gas", "nuclear", "hydro", "solar", "wind"]].sum()
    a.index = M.SRC
    rows.append({"fy_end": 2026, "kind": "actual", **{f"{s}_twh": a[s] for s in M.SRC}, "total_twh": a.sum(),
                 "co2_mt": 0.96 * a.coal + 0.40 * a.gas,
                 **{f"{s}_gw": v for s, v in dict(coal=221.9 + 6.6, gas=20.1, nuclear=8.78, hydro=51.4, solar=150.3, wind=56.1).items()},
                 "bess_gw": np.nan, "psp_gw": 7.43})
    for y, o in res.items():
        S = M.summarise(o); G = o["gen"]; C = o["cap"]
        rows.append({"fy_end": y, "kind": "model", **{f"{s}_twh": G[s].sum() for s in M.SRC}, "total_twh": G.sum().sum(),
                     "co2_mt": o["co2"], **{f"{s}_gw": C[s].sum() for s in M.SRC}, "bess_gw": o["bess"].sum(),
                     "psp_gw": o["psp"].sum(), "co2_cap_mt": CO2[y], "co2_over_cap_mt": o["co2_excess"],
                     "unserved_twh": o["unserved"], "cost_rs_per_kwh": S["cost_rs_per_kwh"], "co2_shadow_rs_per_t": S["co2_shadow_rs_per_t"]})
        for r in M.REG:
            for s in M.SRC:
                regrows.append({"fy_end": y, "region": r, "source": s, "twh": G.loc[r, s], "gw": C.loc[r, s]})
        print(f"{y}: status {o['status']}, unserved {o['unserved']:.1f} TWh, CO2 {o['co2']:.0f} (cap {CO2[y]}, over {o['co2_excess']:.0f})")
    for r in M.REG:
        for s, col in zip(M.SRC, ["coal_lignite", "gas", "nuclear", "hydro", "solar", "wind"]):
            regrows.append({"fy_end": 2026, "region": r, "source": s, "twh": act.loc[r, col], "gw": np.nan})
    P = pd.DataFrame(rows)
    for s in M.SRC:
        P[f"{s}_pct"] = P[f"{s}_twh"] / P.total_twh * 100
    P["non_fossil_pct"] = 100 - P.coal_pct - P.gas_pct
    P.round(2).to_csv(M.OUT / "pathway_national.csv", index=False)
    pd.DataFrame(regrows).round(2).to_csv(M.OUT / "pathway_regional.csv", index=False)
    pd.set_option("display.width", 250)
    print(P[["fy_end", "kind", "total_twh"] + [f"{s}_pct" for s in M.SRC] + ["non_fossil_pct", "co2_mt"]].round(1).to_string(index=False))
    print(P[["fy_end"] + [f"{s}_gw" for s in M.SRC] + ["bess_gw", "psp_gw"]].round(0).to_string(index=False))
    # Continuity checks
    caps = P.set_index("fy_end")
    for s in ["solar", "wind", "nuclear", "hydro"]:
        seq = caps[f"{s}_gw"].values
        assert all(np.diff(seq) >= -1e-6), f"{s} capacity falls along the path: {seq}"
    print("Capacity never falls along the path for solar/wind/nuclear/hydro: OK")
