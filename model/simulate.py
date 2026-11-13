"""Monte Carlo uncertainty, tornado sensitivity, regional roll-up and charts for the generation-only demand model."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
import demand_gen as dm
from regional import regional

OUT = dm.OUT; T = dm.T_FY
rng = np.random.default_rng(2047)
BASE = dm.SCEN["Base"]; LOW = dm.SCEN["Low"]; HIGH = dm.SCEN["High"]
N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 1500

# ------------------------------------------------------------------ Monte Carlo
def draw():
    tri = lambda lo, mo, hi: rng.triangular(lo, mo, hi)
    dc40 = tri(100, 191, 260)
    return dict(gdp=float(np.clip(rng.normal(0.065, 0.007), 0.045, 0.085)), pop_2047=tri(1600, 1665, 1720),
                b=float(np.clip(rng.normal(dm.B_HAT, dm.B_SE), 0.45, 1.05)), k=rng.uniform(0.60, 0.90), c=0.0,
                factor_now=1.12, bridge_2047=rng.uniform(1.06, 1.16), ev_twh_2047=tri(LOW["ev_twh_2047"], BASE["ev_twh_2047"], HIGH["ev_twh_2047"]),
                dc_twh_2040=dc40, dc_twh_2047=dc40 * rng.uniform(1.10, 1.45), h2_mt_2047=tri(5, 12, 25), kwh_per_kg=tri(45, 48, 52))

t0 = time.time(); sims = []
for i in range(N_RUNS):
    p = draw(); n = dm.run(p)
    sims.append({**p, **{f"{k}_{y}": n.loc[y, k] for y in (2031, 2036, 2041, T) for k in ("gen_grid", "gen_total")},
                 "gen_organic_2047": n.loc[T, "gen_organic"], "gen_ev_dc_2047": n.loc[T, "gen_ev_dc"], "gen_h2_2047": n.loc[T, "gen_h2"]})
mc = pd.DataFrame(sims); mc.to_csv(OUT / "v2_montecarlo.csv", index=False)
q = mc[[f"gen_grid_{T}", f"gen_total_{T}", "gen_organic_2047", "gen_ev_dc_2047", "gen_h2_2047"]].quantile([0.1, 0.5, 0.9]).T.round(0)
q.columns = ["P10", "P50", "P90"]
print(f"Monte Carlo: {N_RUNS} runs in {time.time()-t0:.0f}s\n", q.to_string())
q.to_csv(OUT / "v2_mc_quantiles_2047.csv")

# ------------------------------------------------------------------ tornado (one-at-a-time swings, total generation)
base_total = dm.run(BASE).loc[T, "gen_total"]
SW = {"GDP growth (5.5% / 7.5%)": ("gdp",), f"Income elasticity ({dm.B_HAT-dm.B_SE:.2f} / {dm.B_HAT+dm.B_SE:.2f})": ("b",), "Elasticity decay k (0.60 / 0.90)": ("k",),
      "Population 2047 (1.60 / 1.72 bn)": ("pop_2047",), "Green H2 (5 / 25 Mt)": ("h2_mt_2047", "kwh_per_kg"),
      "EV fleet (186 / 977 TWh)": ("ev_twh_2047",), "Data centres (120 / 380 TWh)": ("dc_twh_2040", "dc_twh_2047"),
      "Delivery factor for new loads (1.08 / 1.14)": ("bridge_2047",)}
tor = []
for name, keys in SW.items():
    lo, hi = dict(BASE), dict(BASE)
    for k in keys:
        lo[k], hi[k] = LOW[k], HIGH[k]
    tor.append({"driver": name, "low": dm.run(lo).loc[T, "gen_total"] - base_total, "high": dm.run(hi).loc[T, "gen_total"] - base_total})
tor = pd.DataFrame(tor); tor["span"] = tor.high - tor.low; tor = tor.sort_values("span")
tor.round(0).to_csv(OUT / "v2_tornado.csv", index=False)
print("\nTornado (change in 2047 total generation vs base {:.0f} TWh):\n".format(base_total), tor.round(0).to_string(index=False))

# ------------------------------------------------------------------ regional roll-up (Base)
rg, nb = regional(BASE, [dm.BASE_FY, T])
a = rg[rg.fy_end == dm.BASE_FY].set_index("region"); z = rg[rg.fy_end == T].set_index("region")
r = pd.DataFrame({"gen_fy26_twh": a.gen_total_twh, "organic_2047_twh": z.organic_twh, "ev_2047_twh": z.ev_twh,
                  "dc_2047_twh": z.dc_twh, "gen_grid_2047_twh": z.gen_grid_twh, "gen_h2_2047_twh": z.gen_h2_twh,
                  "gen_total_2047_twh": z.gen_total_twh})
r["growth_x"] = r.gen_total_2047_twh / r.gen_fy26_twh
r = r.round(1); r.loc["India"] = r.sum(numeric_only=True); r.loc["India", "growth_x"] = round(r.loc["India", "gen_total_2047_twh"] / r.loc["India", "gen_fy26_twh"], 2)
print("\nRegional 2047 (Base):\n", r.to_string())
r.to_csv(OUT / "v2_regional_2047_base.csv")

# ------------------------------------------------------------------ charts
hist = dm.nat.generation_bu
fig, ax = plt.subplots(figsize=(9.5, 5.2))
ax.plot(hist.index, hist.values, color="#222", lw=2.2, label="Actual generation (CEA)")
yrs = list(range(dm.BASE_FY, T + 1))
paths = {k: dm.run(v) for k, v in dm.SCEN.items()}
ax.fill_between(yrs, paths["Low"].loc[yrs, "gen_total"], paths["High"].loc[yrs, "gen_total"], color="#2a6fdb", alpha=0.10, label="Low–High scenarios")
ax.plot(yrs, paths["Base"].loc[yrs, "gen_total"], color="#2a6fdb", lw=2.4, label="Base: total incl. green H₂")
ax.plot(yrs, paths["Base"].loc[yrs, "gen_grid"], color="#2a6fdb", lw=1.6, ls="--", label="Base: grid demand only")
for y, col in [(T, "gen_total")]:
    p10, p50, p90 = mc[f"{col}_{y}"].quantile([.1, .5, .9])
    ax.errorbar(y + 0.5, p50, yerr=[[p50 - p10], [p90 - p50]], fmt="o", color="#2a6fdb", capsize=5, label="Monte Carlo P10–P90 (2047)")
ax.errorbar(T + 1.3, 5643.5, yerr=389.5, fmt="s", color="#d9480f", capsize=5, label="Published 2047 scenarios (5,254–6,033)")
ax.set_xlabel("Financial year ending"); ax.set_ylabel("Electricity generated (TWh)")
ax.set_title("India electricity generation requirement to 2047 — model v2 (generation basis)"); ax.grid(alpha=.3); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.tight_layout(); fig.savefig(OUT / "v2_national_fan.png", dpi=160)

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(tor.driver, tor.low, color="#94b8f0"); ax.barh(tor.driver, tor.high, color="#2a6fdb")
ax.axvline(0, color="#333", lw=.8); ax.set_xlabel(f"Change in 2047 generation vs base ({base_total:,.0f} TWh)")
ax.set_title("What moves the 2047 number most"); ax.grid(axis="x", alpha=.3); fig.tight_layout(); fig.savefig(OUT / "v2_tornado.png", dpi=160)

rr = r.drop(index="India")
fig, ax = plt.subplots(figsize=(8.5, 4.4)); x = np.arange(len(rr)); w = .38
ax.bar(x - w/2, rr.gen_fy26_twh, w, color="#999", label="FY26 requirement (weather-smoothed)")
ax.bar(x + w/2, rr.gen_grid_2047_twh, w, color="#2a6fdb", label="2047 grid demand")
ax.bar(x + w/2, rr.gen_h2_2047_twh, w, bottom=rr.gen_grid_2047_twh, color="#7fd1ae", label="2047 green H₂")
ax.set_xticks(x); ax.set_xticklabels(rr.index); ax.set_ylabel("TWh"); ax.set_title("Regional generation requirement — Base")
ax.legend(frameon=False); ax.grid(axis="y", alpha=.3); fig.tight_layout(); fig.savefig(OUT / "v2_regional.png", dpi=160)
print("\nCharts written.")
