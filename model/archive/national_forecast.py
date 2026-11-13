"""INNOTHON 2026 - v0 national forecast of India's electricity GENERATION to FY2046-47.

Three independent methods, combined into an ensemble, under Low / Base / High scenarios:
  A. GDP-elasticity model   : generation grows with real GDP at an elasticity that is
                              estimated on history and drifts to a 2047 value.
  B. Per-capita saturation  : per-capita generation follows a logistic curve calibrated on
                              history toward a scenario ceiling, multiplied by population.
  C. Damped-trend time series: Holt exponential smoothing on log(generation); a pure-trend
                              cross-check with no economic drivers.

Metric: energy generated (BU = TWh). Usage: python model/national_forecast.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parents[1]
hist = pd.read_csv(ROOT / "data" / "national_history.csv")
BASE_YEAR, END_YEAR = 2026, 2047
years = np.arange(BASE_YEAR, END_YEAR + 1)
G0 = hist.loc[hist.fy_end_year == BASE_YEAR, "generation_bu"].item()
P0 = hist.loc[hist.fy_end_year == BASE_YEAR, "population_mn"].item()

# ---------------------------------------------------------------- scenarios
SCENARIOS = {
    #            pop 2047 (mn)  GDP growth   elasticity 2047   per-capita ceiling (kWh)
    "Low":  dict(pop_2047=1600, gdp=0.055, elast_end=0.60, pc_ceiling=4500),
    "Base": dict(pop_2047=1665, gdp=0.065, elast_end=0.70, pc_ceiling=6000),  # UN WPP 2024 medium
    "High": dict(pop_2047=1700, gdp=0.075, elast_end=0.80, pc_ceiling=7500),
}
WEIGHTS = {"A": 0.4, "B": 0.4, "C": 0.2}


def population_path(pop_2047):
    rate = (pop_2047 / P0) ** (1 / (END_YEAR - BASE_YEAR)) - 1
    return P0 * (1 + rate) ** (years - BASE_YEAR)


# ---------------------------------------------------- A: GDP elasticity
X = pd.DataFrame({"log_gdp": np.log(hist.gdp_cr_2011_12),
                  "covid": (hist.fy_end_year == 2021).astype(float)})
reg = sm.OLS(np.log(hist.generation_bu), sm.add_constant(X)).fit()
ELAST_HIST = reg.params["log_gdp"]


def method_a(s):
    e = np.linspace(ELAST_HIST, s["elast_end"], len(years))
    g = [G0]
    for et in e[1:]:
        g.append(g[-1] * (1 + s["gdp"]) ** et)
    return np.array(g)


# ---------------------------------------------- B: per-capita saturation
pc_hist = hist.generation_bu * 1e3 / hist.population_mn  # kWh per person


def method_b(s):
    K = s["pc_ceiling"]
    # logistic: pc = K / (1 + exp(-(a + r t)))  ->  log(pc/(K-pc)) linear in t
    mask = ~hist.fy_end_year.isin([2020, 2021])
    t = hist.fy_end_year[mask] - BASE_YEAR
    z = np.log(pc_hist[mask] / (K - pc_hist[mask]))
    r = np.polyfit(t, z, 1)[0]
    z0 = np.log(pc_hist.iloc[-1] / (K - pc_hist.iloc[-1]))  # anchor on latest actual
    pc = K / (1 + np.exp(-(z0 + r * (years - BASE_YEAR))))
    return pc * population_path(s["pop_2047"]) / 1e3, r


# -------------------------------------------------- C: damped trend
hw = ExponentialSmoothing(np.log(hist.generation_bu.values), trend="add",
                          damped_trend=True).fit()
c_path = np.exp(np.concatenate([[np.log(G0)], hw.forecast(END_YEAR - BASE_YEAR)]))

# ------------------------------------------------------------- run
rows, paths = [], {}
for name, s in SCENARIOS.items():
    a = method_a(s)
    b, r = method_b(s)
    ens = WEIGHTS["A"] * a + WEIGHTS["B"] * b + WEIGHTS["C"] * c_path
    paths[name] = ens
    rows.append({
        "scenario": name,
        "A_gdp_elasticity_TWh": a[-1], "B_per_capita_TWh": b[-1], "C_damped_trend_TWh": c_path[-1],
        "ensemble_2047_TWh": ens[-1],
        "CAGR_2026_47_pct": ((ens[-1] / G0) ** (1 / 21) - 1) * 100,
        "per_capita_2047_kWh": ens[-1] * 1e3 / s["pop_2047"],
    })
res = pd.DataFrame(rows).round(1)

out = ROOT / "out"
res.to_csv(out / "national_2047_summary.csv", index=False)
pd.DataFrame({"fy_end_year": years, **{k: v.round(1) for k, v in paths.items()}}
             ).to_csv(out / "national_paths.csv", index=False)

print(f"Historical GDP elasticity of generation: {ELAST_HIST:.3f} "
      f"(R^2 = {reg.rsquared:.3f})")
print(f"Damped-trend phi = {hw.params['damping_trend']:.3f}")
print(res.to_string(index=False))

# ------------------------------------------------------------- chart
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(hist.fy_end_year, hist.generation_bu, color="#222", lw=2, label="Actual (CEA)")
ax.fill_between(years, paths["Low"], paths["High"], color="#2a6fdb", alpha=0.15,
                label="Low-High range")
ax.plot(years, paths["Base"], color="#2a6fdb", lw=2.2, label="Base (ensemble)")
ax.plot(years, c_path, color="#999", lw=1, ls="--", label="Trend-only check (C)")
for lo, hi, lab in [(5254, 6033, "Published 2047 scenarios")]:
    ax.errorbar(END_YEAR + 0.6, (lo + hi) / 2, yerr=(hi - lo) / 2, fmt="o", color="#d9480f",
                capsize=4, label=lab)
ax.set_xlabel("Financial year ending")
ax.set_ylabel("Electricity generated (TWh)")
ax.set_title("India electricity generation: history and 2047 forecast (v0)")
ax.grid(alpha=0.3)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(out / "national_forecast_v0.png", dpi=160)
