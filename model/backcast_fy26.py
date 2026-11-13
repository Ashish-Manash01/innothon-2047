"""Backcast validation: does the mix LP reproduce India's ACTUAL FY2025-26 generation mix by region when given
today's fleet (pinned) and today's regional demand?  This tests the dispatch logic, cost ordering, time slices,
transmission and coal minimum-load rules against reality before trusting the 2047 answer.

Setup
  - Capacities pinned to CEA 31-03-2026 by region (coal+lignite, gas, nuclear, hydro). Solar & wind capacities set
    so their maximum energy equals actual FY26 solar/wind output by region (curtailment is negligible in FY26).
  - Regional demand = FY26 regional production requirement on a GENERATION basis (own generation + net inter-regional
    imports, Grid-India; demand_gen.NEED), scaled so the national total
    equals actual modelled generation (all sources except bio & small hydro, which are netted off as must-run).
  - No new build, no new storage, no CO2 cap, transmission = today's corridors (x1), load factor 0.80, bridge 1.077.
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import mix_lp as M

REG = M.REG
act = pd.read_csv(M.D / "region_generation_fy26.csv", index_col=0).reindex(REG)
import demand_gen as dm
req = dm.NEED.loc[2026].reindex(REG) / 1e3
modelled = act[["coal_lignite", "gas", "nuclear", "hydro", "solar", "wind"]].sum(axis=1)
dem_total = modelled.sum() + M.BHUTAN_TWH
grid = req / req.sum() * dem_total
h2 = pd.Series(0.0, index=REG)

capm = M.capm
fixed = {}
for r in REG:
    fixed[(r, "coal")] = capm.loc[r, "coal"] / 1e3 + capm.loc[r, "lignite"] / 1e3
    fixed[(r, "gas")] = capm.loc[r, "gas"] / 1e3
    fixed[(r, "nuclear")] = capm.loc[r, "nuclear"] / 1e3
    fixed[(r, "hydro")] = capm.loc[r, "hydro"] / 1e3
    fixed[(r, "solar")] = act.loc[r, "solar"] / (8.76 * M.CF.loc[r, "solar"])
    fixed[(r, "wind")] = act.loc[r, "wind"] / (8.76 * M.CF.loc[r, "wind"])
cfg = dict(fixed_cap=fixed, coal_min=pd.Series({r: fixed[(r, "coal")] for r in REG}),
           nuc_min=pd.Series({r: fixed[(r, "nuclear")] for r in REG}), hydro_min=pd.Series({r: fixed[(r, "hydro")] for r in REG}),
           psp_min=7.43, no_new_storage=True, load_factor=0.80, bridge=1.077, reserve=0.0)
o = M.solve(co2_cap=5000, tx_mult=1.0, dem=(grid, h2), cfg=cfg, label="Backcast FY26", nuclear_cap=20,
            wind_cap=500, solar_cap=500, hydro_cap=200)
assert o["status"] == "Optimal", o["status"]
G = o["gen"]
cmp_rows = []
for r in REG + ["India"]:
    a = act.loc[r] if r != "India" else act.sum()
    g = G.loc[r] if r != "India" else G.sum()
    for s, col in [("coal", "coal_lignite"), ("gas", "gas"), ("nuclear", "nuclear"), ("hydro", "hydro"), ("solar", "solar"), ("wind", "wind")]:
        cmp_rows.append({"region": r, "source": s, "actual_twh": round(a[col], 1), "model_twh": round(g[s], 1),
                         "diff_twh": round(g[s] - a[col], 1)})
C = pd.DataFrame(cmp_rows)
C.to_csv(M.OUT / "backcast_fy26.csv", index=False)
piv = C.pivot_table(index="region", columns="source", values=["actual_twh", "model_twh"]).reindex(REG + ["India"])
pd.set_option("display.width", 220)
print(piv.round(0).to_string())
nat = C[C.region == "India"].set_index("source")
tot_a, tot_m = nat.actual_twh.sum(), nat.model_twh.sum()
print("\nNational shares actual vs model (%):")
print(pd.DataFrame({"actual": nat.actual_twh / tot_a * 100, "model": nat.model_twh / tot_m * 100}).round(1).to_string())
reg_coal_err = (C[(C.source == "coal") & (C.region != "India")].diff_twh.abs().sum()) / nat.loc["coal", "actual_twh"] * 100
print(f"\nRegional coal allocation error (sum |diff| / national coal): {reg_coal_err:.1f}%")
print("Unserved TWh:", round(o["unserved"], 2), " Flows (TWh):", o["flows"][o["flows"] > 1].round(0).to_dict())
