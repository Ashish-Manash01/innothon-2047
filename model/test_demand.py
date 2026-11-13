"""Verification tests for the generation-only demand model (demand_gen.py). Each test FAILS if a specific bug exists.
Run: python model/test_demand.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_gen as dm
from regional import regional

R = []
def check(name, ok, detail=""):
    R.append((name, "PASS" if ok else "FAIL", detail))

B = dict(dm.SCEN["Base"])
n, st = dm.run(B, detail=True)

# 1 Data: regional generation history reconciles with national generation (MoP) every year
g = pd.read_csv(dm.D / "region_generation_history.csv").groupby("fy_end_year").generation_mu.sum()
bh = pd.read_csv(dm.D / "bhutan_import_history.csv").set_index("fy_end_year").bhutan_mu
gap = ((g + bh) / 1e3 / dm.nat.generation_bu.reindex(g.index) - 1).abs().max() * 100
check("Regions + Bhutan = national generation (FY19-26)", gap < 0.1, f"max gap {gap:.3f}%")

# 2 Data: inter-regional net flows roughly balance (international exchanges are small)
f = dm.FLOW_R.sum(axis=1)
check("Net inter-regional flows balance within 2 TWh", f.abs().max() < 2000, f"max imbalance {f.abs().max():.0f} MU")

# 3 Regional requirement sums to national generation each year
nd = dm.NEED.sum(axis=1) / 1e3
check("Regional requirement = national generation", np.allclose(nd.values, dm.nat.generation_bu.reindex(nd.index).values, rtol=1e-3),
      f"{nd.round(1).to_dict()}")

# 4 Base year = weather-smoothed FY26 national generation, split by FY24-26 requirement shares
check("Base year = smoothed FY26", abs(n.loc[2026, "gen_organic"] - dm.G26) < 0.01, f"{n.loc[2026,'gen_organic']:.1f} vs {dm.G26:.1f}")
check("Smoothed base within 5% of actual FY26", abs(dm.G26 / dm.G26_ACTUAL - 1) < 0.05, f"{dm.G26:.0f} vs actual {dm.G26_ACTUAL:.0f}")

# 5 Zero GDP growth -> per-capita generation does not rise; zero new loads -> adder ~0
Z = dict(B, gdp=0.0, c=0.0, ev_twh_2047=4.0, dc_twh_2040=10.0, dc_twh_2047=10.0, h2_mt_2047=0.0)
nz, sz = dm.run(Z, detail=True)
pc = sz.groupby("fy_end").apply(lambda d: d.organic_twh.sum() / d.pop_k.sum())
check("Zero GDP growth -> per-capita generation does not rise", pc.diff().dropna().max() <= 1e-12, f"{pc.iloc[0]*1e6:.0f} -> {pc.iloc[-1]*1e6:.0f} kWh")
check("Zero new loads -> EV/DC adder ~0", abs(nz.loc[2047, "gen_ev_dc"]) < 1.0, f"{nz.loc[2047,'gen_ev_dc']:.2f} TWh")

# 6 Elasticity identity per region in year 1
a, b_ = st[st.fy_end == 2026].set_index("region"), st[st.fy_end == 2027].set_index("region")
el = np.log(b_.kwh_gen_pc / a.kwh_gen_pc) / np.log((b_.gsdp_index / b_.pop_k) / (a.gsdp_index / a.pop_k))
exp_b = B["b"] * (1 - (1 - B["k"]) / 21)
check("Year-1 regional elasticity = b_t", np.allclose(el.values, exp_b, atol=1e-9), f"expected {exp_b:.4f}")

# 7 Units and anchors
check("H2 units: 12 Mt x 48 kWh/kg = 576 TWh", abs(n.loc[2047, "h2_twh"] - 576) < 0.5, f"{n.loc[2047,'h2_twh']:.1f}")
check("Population FY2047 = 1,665 mn", abs(n.loc[2047, "pop_mn"] - 1665) < 0.5, f"{n.loc[2047,'pop_mn']:.1f}")
check("Regions sum to national organic (all years)", np.allclose(st.groupby("fy_end").organic_twh.sum().values, n.gen_organic.values, atol=1e-6))
rg, _ = regional(B, [2030, 2047])
check("Regional roll-up = national total", abs(rg[rg.fy_end == 2047].gen_total_twh.sum() - n.loc[2047, "gen_total"]) < 0.5)

# 8 Monotonicity
for k, lo, hi in [("gdp", .06, .07), ("b", .70, .80), ("pop_2047", 1630, 1700), ("h2_mt_2047", 8, 16), ("k", .7, .8), ("bridge_2047", 1.08, 1.12)]:
    x = dm.run(dict(B, **{k: lo})).loc[2047, "gen_total"]; y = dm.run(dict(B, **{k: hi})).loc[2047, "gen_total"]
    check(f"Monotone in {k}", y > x, f"{x:.0f} -> {y:.0f}")

# 9 Back-test on GENERATION: elasticity fitted on FY11-FY19 only, project FY20-FY26 with actual GDP and population
nn = dm.NAT.copy()
fd = nn[["lg", "ly"]].diff().join(nn[["covid", "rebound"]]).dropna()
import statsmodels.api as sm
b19 = sm.OLS(fd.loc[:2019].lg, fd.loc[:2019][["ly"]]).fit().params["ly"]
covid = dm.M_FD.params[["covid", "rebound"]]
errs = {}
for yy in (2024, 2025, 2026):
    pl = nn.lg.loc[2019] + b19 * (nn.ly.loc[yy] - nn.ly.loc[2019]) + covid.sum()
    errs[yy] = (np.exp(pl) * nn.population_mn.loc[yy] / 1e3 / nn.generation_bu.loc[yy] - 1) * 100
mae = np.mean(np.abs(list(errs.values())))
check("Back-test: b fitted to FY19 only, FY24-26 mean abs error < 5%", mae < 5,
      f"b={b19:.3f}; errors " + ", ".join(f"FY{y-2000}: {e:+.1f}%" for y, e in errs.items()))
nv = {yy: (nn.generation_bu.loc[2019] * (nn.generation_bu.loc[2019] / nn.generation_bu.loc[2012]) ** ((yy - 2019) / 7) / nn.generation_bu.loc[yy] - 1) * 100 for yy in (2024, 2025, 2026)}
check("INFO naive trend (FY12-19 growth carried forward), same years", True, ", ".join(f"FY{y-2000}: {e:+.1f}%" for y, e in nv.items()))
check("Levels cross-check elasticity within 2 SE of growth estimate", abs(dm.B_LEVELS - dm.B_HAT) < 2 * dm.B_SE,
      f"{dm.B_LEVELS:.3f} vs {dm.B_HAT:.3f}")

# 10 Monte Carlo complete
mc = pd.read_csv(dm.OUT / "v2_montecarlo.csv")
check("Monte Carlo runs complete & finite", mc.filter(like="gen_").notna().all().all() and len(mc) == 2000, f"{len(mc)} runs")

# 11 Electrification layer off by default, additive when on
h, c = dm.elec_2047("base"); n1 = dm.run(dict(B, heat_twh_2047=h, cook_twh_2047=c))
check("Electrification layer off by default", abs(n.loc[2047, "gen_elec"]) < 1e-9)
check("Electrification adds (heat+cook) x delivery factor", abs((n1.loc[2047, "gen_total"] - n.loc[2047, "gen_total"]) - (h + c) * n.loc[2047, "bridge"]) < 0.01,
      f"+{n1.loc[2047,'gen_total'] - n.loc[2047,'gen_total']:.0f} TWh")

out = pd.DataFrame(R, columns=["test", "result", "detail"])
print(out.to_string(index=False))
out.to_csv(dm.OUT / "v2_tests.csv", index=False)
fails = (out.result == "FAIL").sum()
print("\n", (out.result == "PASS").sum(), "/", len(out), "passed")
sys.exit(1 if fails else 0)
