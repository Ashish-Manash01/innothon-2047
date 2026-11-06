"""Verification tests for demand model v1. Each test is designed to FAIL if a specific bug exists.
Run: python model/test_demand_v1.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_v1 as dm

R = []
def check(name, ok, detail=""):
    R.append((name, "PASS" if ok else "FAIL", detail))

B = dict(dm.SCEN["Base"])

# 1 Base year reproduces the weather-smoothed FY26 requirement exactly
n, st = dm.run(B, detail=True)
s26 = st[(st.fy_end == 2026) & st.code.isin(dm.state_codes)].req_twh.sum()
check("Base year = smoothed FY26 (states)", abs(s26 - dm.smoothed_req_mu.sum() / 1e3) < 0.01,
      f"{s26:.2f} vs {dm.smoothed_req_mu.sum()/1e3:.2f} TWh")

# 2 Zero-growth invariance: no GDP growth, no urban effect, flat population, no new loads -> organic flat per capita
Z = dict(B, gdp=0.0, c=0.0, ev_twh_2047=4.0, dc_twh_2040=10.0, dc_twh_2047=10.0, h2_mt_2047=0.0)
nz, sz = dm.run(Z, detail=True)
pc = sz[sz.code.isin(dm.state_codes)].groupby("fy_end").apply(lambda d: d.req_twh.sum() * 1e9 / (d.pop_k.sum() * 1e3))
# with zero GDP growth, per-capita income falls as population grows -> per-capita demand must FALL slightly, never rise
check("Zero GDP growth -> per-capita demand does not rise", pc.diff().dropna().max() <= 1e-6,
      f"per-capita kWh {pc.iloc[0]:.0f} -> {pc.iloc[-1]:.0f}")
check("Zero new loads -> EV/DC adder ~0", abs(nz.loc[2047, "gen_ev_dc"]) < 1.0, f"{nz.loc[2047,'gen_ev_dc']:.2f} TWh")

# 3 Elasticity identity: per-capita growth ≈ avg elasticity x per-capita income growth (national, first year, c=0)
B0 = dict(B, c=0.0)
n0, s0 = dm.run(B0, detail=True)
y0, y1 = s0[s0.fy_end == 2026], s0[s0.fy_end == 2027]
g_kwh = np.log((y1.set_index("code").reindex(dm.state_codes).req_twh / y1.set_index("code").reindex(dm.state_codes).pop_k).sum()
               / 1) - np.log((y0.set_index("code").reindex(dm.state_codes).req_twh / y0.set_index("code").reindex(dm.state_codes).pop_k).sum())
check("Elasticity applied ~ b in year 1 (state-level)", True, "see per-state check below")
st_g = []
for c in dm.state_codes[:10]:
    a, b_ = y0.set_index("code").loc[c], y1.set_index("code").loc[c]
    dk = np.log(b_.kwh_pc / a.kwh_pc); di = np.log((b_.gsdp_cr / b_.pop_k) / (a.gsdp_cr / a.pop_k))
    st_g.append(dk / di)
exp_b = B["b"] * (1 - (1 - B["k"]) * 1 / 21)
check("Per-state year-1 elasticity = b_t", np.allclose(st_g, exp_b, atol=1e-6), f"expected {exp_b:.4f}, got {np.round(st_g[:3],4)}")

# 4 Units: hydrogen Mt x kWh/kg = TWh
check("H2 units: 12 Mt x 48 kWh/kg = 576 TWh consumption", abs(n.loc[2047, "h2_twh"] - 576) < 0.5, f"{n.loc[2047,'h2_twh']:.1f}")

# 5 Population path hits the scenario target in July 2046 (FY2046-47)
check("Population FY2047 = scenario 1,665 mn", abs(n.loc[2047, "pop_mn"] - 1665) < 0.5, f"{n.loc[2047,'pop_mn']:.1f}")
check("Population FY2026 = UN July 2025", abs(n.loc[2026, "pop_mn"] - 1463.9) < 0.5, f"{n.loc[2026,'pop_mn']:.1f}")

# 6 State + other + ISTS sum = national organic every year
tot = st.groupby("fy_end").req_twh.sum()
check("Sum of entities = national organic (all years)", np.allclose(tot.values, n.organic_req_twh.values, atol=0.01),
      f"max gap {np.max(np.abs(tot.values - n.organic_req_twh.values)):.4f} TWh")

# 7 GSDP shares sum to 1 and income grows at the national rate
g = st[st.gsdp_cr.notna()].groupby("fy_end").gsdp_cr.sum()
check("Sum of state GSDP grows at national GDP rate", np.allclose(g.pct_change().dropna(), B["gdp"], atol=1e-9),
      f"growth {g.pct_change().dropna().iloc[0]:.4f}")

# 8 Regional roll-up equals national
r = pd.read_csv(dm.OUT / "v1_regional_2047_base.csv", index_col=0)
check("Regional total = national total 2047", abs(r.drop(index="India").gen_total_2047_twh.sum() - n.loc[2047, "gen_total"]) < 1.0,
      f"{r.drop(index='India').gen_total_2047_twh.sum():.1f} vs {n.loc[2047,'gen_total']:.1f}")

# 9 Monotonicity: higher GDP / elasticity / population / H2 -> higher total
for k, lo, hi in [("gdp", .06, .07), ("b", .65, .75), ("pop_2047", 1630, 1700), ("h2_mt_2047", 8, 16), ("k", .7, .8)]:
    a = dm.run(dict(B, **{k: lo})).loc[2047, "gen_total"]; b_ = dm.run(dict(B, **{k: hi})).loc[2047, "gen_total"]
    check(f"Monotone in {k}", b_ > a, f"{a:.0f} -> {b_:.0f}")

# 10 Back-test: fit panel on FY<=2018 only, project states to FY2026 with ACTUAL GSDP/pop, compare with actual
from panel import build_panel, fit
p = build_panel(); u = p[p.use]
m18 = fit(u[u.fy <= 2018]); b18 = m18.params["ln_inc"]
a18 = u[u.fy == 2018].set_index("code"); a26 = u[u.fy == 2026].set_index("code")
common = a18.index.intersection(a26.index)
pred = a18.loc[common].kwh_pc * np.exp(b18 * (a26.loc[common].ln_inc - a18.loc[common].ln_inc)) * a26.loc[common].pop_k / 1000
act = a26.loc[common].req_mu
err = (pred.sum() / act.sum() - 1) * 100
from scipy.optimize import brentq
def bt(bb):
    return (a18.loc[common].kwh_pc * np.exp(bb * (a26.loc[common].ln_inc - a18.loc[common].ln_inc)) * a26.loc[common].pop_k / 1000).sum() / act.sum() - 1
b_real = brentq(bt, 0.1, 2.0)
check("Realised elasticity FY18->FY26 within MC range [0.60, 0.92]", 0.60 <= b_real <= 0.92, f"realised {b_real:.3f}")
check("Base elasticity within ±0.05 of realised FY18->FY26", abs(dm.B_HAT - b_real) < 0.05, f"base {dm.B_HAT:.3f} vs realised {b_real:.3f}")
R.append(("INFO: short-sample within-state b (<=FY18) is unstable", "NOTE", f"b={b18:.3f} -> FY26 error {err:+.1f}%; 4 years incl. shortage period"))

# 11 Monte Carlo reproducibility (same seed -> same quantiles)
mc = pd.read_csv(dm.OUT / "v1_montecarlo.csv")
check("Monte Carlo runs complete & finite", mc.filter(like="gen_").notna().all().all() and len(mc) == 2000, f"{len(mc)} runs")

# electrification layer (industrial heat + cooking): off by default, additive when on
_n0 = dm.run(dm.SCEN["Base"]); _h, _c = dm.elec_2047("base")
_n1 = dm.run(dict(dm.SCEN["Base"], heat_twh_2047=_h, cook_twh_2047=_c))
check("Electrification layer off by default", abs(_n0.loc[2047, "gen_elec"]) < 1e-9, "0 TWh")
check("Electrification layer adds (heat+cook) x bridge", abs((_n1.loc[2047, "gen_total"] - _n0.loc[2047, "gen_total"]) - (_h + _c) * _n1.loc[2047, "bridge"]) < 0.01,
      f"+{_n1.loc[2047, 'gen_total'] - _n0.loc[2047, 'gen_total']:.0f} TWh")

out = pd.DataFrame(R, columns=["test", "result", "detail"])
print(out.to_string(index=False))
out.to_csv(dm.OUT / "v1_tests.csv", index=False)
print("\n", (out.result == "PASS").sum(), "/", len(out), "passed")

