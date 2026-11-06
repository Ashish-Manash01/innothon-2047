"""Regional generation-mix optimisation for 2047 (linear programme, HiGHS solver).

Decide, for each of 5 grid regions, capacity (GW) and generation (TWh) of coal, gas, nuclear, hydro, solar, wind,
plus 4-hour battery storage (enabler) and inter-regional power flows, to MINIMISE total annual system cost subject to:
  1. Energy balance per region: local generation + imports - exports (with losses) >= demand (+ storage losses)
  2. Resource / land limits: solar <= NISE feasible potential, wind <= NIWE 150 m potential, hydro <= CEA exploitable,
     nuclear <= sites + national 100 GW mission, coal <= national fleet ceiling, gas <= LNG-limited ceiling
  3. Committed assets: hydro & nuclear operating + under construction (+ sanctioned nuclear) are kept
  4. Reliability: firm capacity (capacity credit x GW, incl. storage and firm imports) >= peak x (1 + reserve)
  5. Solar timing: solar used <= daytime share of demand + storage-shifted energy (+ flexible H2 load)
  6. Corridors: flows <= today's corridor capacity x expansion multiplier
  7. Climate: CO2 from coal + gas <= cap
Metric = energy generated (TWh). This is an annual-energy screening model, not an hourly dispatch model.
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pulp

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
A = pd.read_csv(D / "mix_assumptions.csv").set_index("item").value.astype(float)
H = 8.76  # TWh per GW-year at 100%

# ---------------------------------------------------------------- regional data
res = pd.read_csv(D / "state_resources.csv")
rg = res.groupby("cea_region").agg(solar_gwp=("solar_potential_gwp", "sum"), wind_gw=("wind150_potential_gw", "sum"),
                                   hydro_max=("hydro_exploitable_mw", "sum"), hydro_op=("hydro_operating_mw", "sum"),
                                   hydro_uc=("hydro_under_constr_mw", "sum"))
rg["solar_max_gw"] = rg.solar_gwp / 1.25          # DC GWp -> AC GW (DC/AC ratio 1.25)
rg["hydro_max_gw"] = rg.hydro_max / 1e3; rg["hydro_min_gw"] = (rg.hydro_op + rg.hydro_uc) / 1e3
nuc = pd.read_csv(D / "nuclear_sites.csv")
nuc_site = nuc.groupby("cea_region").capacity_mw.sum() / 1e3
nuc_min = nuc[nuc.status.isin(["operating", "under construction", "sanctioned (pre-project)"])].groupby("cea_region").capacity_mw.sum() / 1e3
# 2047 capacity factors: solar/wind by resource quality (assumed); hydro DERIVED from FY26 regional data
CF = pd.DataFrame({
    "coal": 0.80, "gas": 0.60, "nuclear": 0.80,
    "hydro": pd.Series({"Northern": 82.67 / 21.67, "Western": 20.28 / 7.39, "Southern": 43.44 / 13.60,
                        "Eastern": 12.54 / 5.99, "North-Eastern": 8.22 / 2.77}) / H,
    "solar": pd.Series({"Northern": 0.22, "Western": 0.21, "Southern": 0.20, "Eastern": 0.18, "North-Eastern": 0.16}),
    "wind": pd.Series({"Northern": 0.30, "Western": 0.32, "Southern": 0.32, "Eastern": 0.25, "North-Eastern": 0.25}),
}, index=REG)
PITHEAD = {"Eastern", "Western"}   # Odisha/Jharkhand/WB coalfields; Chhattisgarh/MP in Western
CORR = {("Eastern", "Northern"): 22.53, ("Eastern", "Western"): 22.79, ("Western", "Northern"): 38.32,
        ("Eastern", "Southern"): 7.83, ("Western", "Southern"): 22.32, ("Eastern", "North-Eastern"): 3.55,
        ("North-Eastern", "Northern"): 3.00}   # GW, CEA 31-03-2026
BHUTAN_TWH = 7.8   # imports into Eastern grid, held at FY26 level


def demand_2047(which="base"):
    r = pd.read_csv(OUT / "v1_regional_2047_base.csv", index_col=0).drop(index="India")
    grid, h2 = r.gen_grid_2047_twh, r.gen_h2_2047_twh
    if which != "base":  # scale to Monte Carlo quantile, keeping regional shares
        q = pd.read_csv(OUT / "v1_mc_quantiles_2047.csv", index_col=0)
        f_grid = q.loc["gen_grid_2047", which] / grid.sum(); f_h2 = q.loc["gen_h2_2047", which] / h2.sum()
        grid, h2 = grid * f_grid, h2 * f_h2
    return grid.reindex(REG), h2.reindex(REG)


def solve(co2_cap=A.co2_cap_base_mt, nuclear_cap=A.nuclear_cap_national_gw, tx_mult=A.tx_multiplier_base,
          demand="base", solar_cost_mult=1.0, label="Base", verbose=False):
    grid, h2 = demand_2047(demand)
    bridge = 1.06
    peak = grid / bridge / (H * A.load_factor_2047)  # GW, consumption-side peak (H2 electrolysers flexible -> excluded)
    m = pulp.LpProblem("mix2047", pulp.LpMinimize)
    cap = {(r, s): m.add_variable(f"cap_{r[:3]}_{s}", lowBound=0) for r in REG for s in SRC}
    gen = {(r, s): m.add_variable(f"gen_{r[:3]}_{s}", lowBound=0) for r in REG for s in SRC}
    bess = {r: m.add_variable(f"bess_{r[:3]}", lowBound=0) for r in REG}
    flow = {}; ffirm = {}
    for (a, b), gw in CORR.items():
        for x, y in [(a, b), (b, a)]:
            flow[(x, y)] = m.add_variable(f"flow_{x[:3]}_{y[:3]}", lowBound=0)
            ffirm[(x, y)] = m.add_variable(f"firm_{x[:3]}_{y[:3]}", lowBound=0)
        m += flow[(a, b)] + flow[(b, a)] <= gw * tx_mult * H * A.transfer_util, f"corr_energy_{a[:3]}_{b[:3]}"
        m += ffirm[(a, b)] + ffirm[(b, a)] <= gw * tx_mult, f"corr_peak_{a[:3]}_{b[:3]}"
    # ---- objective (₹ crore): fixed (crore/MW-yr x 1000 MW/GW) + variable (₹/kWh x 100 crore/TWh)
    fixed = {"coal": A.coal_fixed, "gas": A.gas_fixed, "nuclear": A.nuclear_fixed, "hydro": A.hydro_fixed,
             "solar": A.solar_fixed * solar_cost_mult, "wind": A.wind_fixed}
    var = lambda r, s: {"coal": A.coal_var_pithead + (0 if r in PITHEAD else A.coal_var_nonpithead_extra),
                        "gas": A.gas_var, "nuclear": A.nuclear_var}.get(s, 0.0)
    m += (pulp.lpSum(fixed[s] * 1000 * cap[(r, s)] + var(r, s) * 100 * gen[(r, s)] for r in REG for s in SRC)
          + pulp.lpSum(A.bess4h_fixed * 1000 * bess[r] for r in REG)
          + pulp.lpSum(A.transfer_cost * 100 * f for f in flow.values()))
    for r in REG:
        for s in SRC:
            m += gen[(r, s)] <= cap[(r, s)] * H * CF.loc[r, s]
        imp = pulp.lpSum(flow[(x, y)] * (1 - A.transfer_loss) for (x, y) in flow if y == r)
        exp = pulp.lpSum(flow[(x, y)] for (x, y) in flow if x == r)
        store_loss = bess[r] * A.bess_throughput * A.bess_loss
        bhutan = BHUTAN_TWH if r == "Eastern" else 0.0
        m += pulp.lpSum(gen[(r, s)] for s in SRC) + bhutan + imp - exp >= grid[r] + h2[r] + store_loss, f"balance_{r[:3]}"
        # resource limits
        m += cap[(r, "solar")] <= rg.solar_max_gw.get(r, 0)
        m += cap[(r, "wind")] <= rg.wind_gw.get(r, 0) if r in rg.index and rg.wind_gw.get(r, 0) > 0 else cap[(r, "wind")] <= 0
        m += cap[(r, "hydro")] <= rg.hydro_max_gw.get(r, 0)
        m += cap[(r, "hydro")] >= rg.hydro_min_gw.get(r, 0)
        m += cap[(r, "nuclear")] >= nuc_min.get(r, 0)
        m += cap[(r, "nuclear")] <= nuc_site.get(r, 0) + max(nuclear_cap - nuc_site.sum(), 0)   # + SMR/BSR allowance
        # reliability: firm capacity incl. storage and firm imports
        cc = {"coal": A.cc_coal, "gas": A.cc_gas, "nuclear": A.cc_nuclear, "hydro": A.cc_hydro, "solar": A.cc_solar, "wind": A.cc_wind}
        firm_in = pulp.lpSum(ffirm[(x, y)] for (x, y) in ffirm if y == r)
        firm_out = pulp.lpSum(ffirm[(x, y)] for (x, y) in ffirm if x == r)
        m += pulp.lpSum(cc[s] * cap[(r, s)] for s in SRC) + A.cc_bess * bess[r] + firm_in - firm_out >= peak[r] * (1 + A.reserve_margin), f"firm_{r[:3]}"
        # solar timing: direct daytime use + flexible H2 + storage-shifted energy
        m += gen[(r, "solar")] <= A.solar_daytime_share * grid[r] + h2[r] + bess[r] * A.bess_throughput + \
             pulp.lpSum(flow[(x, y)] for (x, y) in flow if x == r), f"solar_time_{r[:3]}"
    m += pulp.lpSum(cap[(r, "coal")] for r in REG) <= A.coal_cap_national_gw
    m += pulp.lpSum(cap[(r, "gas")] for r in REG) <= A.gas_cap_national_gw
    m += pulp.lpSum(cap[(r, "nuclear")] for r in REG) <= nuclear_cap
    co2 = pulp.lpSum(0.96 * gen[(r, "coal")] + 0.40 * gen[(r, "gas")] for r in REG)
    m += co2 <= co2_cap, "co2_cap"
    res_ = m.solve(pulp.HiGHS(msg=verbose))
    st = res_.status.name
    CONS = {c.name: c for c in m.constraints()}
    if st != "Optimal":
        return {"label": label, "status": st}
    G = pd.DataFrame({s: {r: gen[(r, s)].value() for r in REG} for s in SRC})
    C = pd.DataFrame({s: {r: cap[(r, s)].value() for r in REG} for s in SRC})
    F = pd.Series({f"{x}->{y}": v.value() for (x, y), v in flow.items()})
    out = dict(label=label, status=st, gen=G, cap=C, bess=pd.Series({r: bess[r].value() for r in REG}), flows=F,
               co2=co2.value(), cost_cr=pulp.value(m.objective), demand=grid + h2, peak=peak,
               co2_dual=CONS["co2_cap"].pi,
               cons=CONS,
               params=dict(co2_cap=co2_cap, nuclear_cap=nuclear_cap, tx_mult=tx_mult, demand=demand, solar_cost_mult=solar_cost_mult))
    return out


def summarise(o):
    G = o["gen"]; tot = G.sum().sum()
    nat = (G.sum() / tot * 100).round(1)
    return {"scenario": o["label"], "total_gen_twh": round(tot, 0), **{f"{s}_%": nat[s] for s in SRC},
            "non_fossil_%": round((G[["nuclear", "hydro", "solar", "wind"]].sum().sum()) / tot * 100, 1),
            "co2_mt": round(o["co2"], 0), "bess_gw": round(o["bess"].sum(), 0),
            "cost_rs_per_kwh": round(o["cost_cr"] / (tot * 100), 2), "co2_shadow_rs_per_t": round(-o["co2_dual"] * 1e7 / 1e6, 0)}


if __name__ == "__main__":
    base = solve(label="Base")
    print("Status:", base["status"])
    G, C = base["gen"], base["cap"]
    print("\nGeneration 2047 by region (TWh):\n", G.round(0).assign(total=G.sum(axis=1).round(0)).to_string())
    print("\nShare of each region's own generation (%):\n", (G.div(G.sum(axis=1), axis=0) * 100).round(1).to_string())
    print("\nCapacity 2047 (GW):\n", C.round(1).assign(bess=base["bess"].round(1)).to_string())
    print("\nNet flows (TWh):\n", base["flows"][base["flows"] > 0.5].round(0).to_string())
    print("\nSummary:", summarise(base))
