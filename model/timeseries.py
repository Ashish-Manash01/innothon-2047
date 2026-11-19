"""Traditional time-series cross-check on national electricity GENERATION (MoP/CEA, FY2009-10 to FY2025-26).

Why: the headline model explains generation with income and population (a structural model). Time-series models
use only the generation series itself, so they are an independent check on the level and on the uncertainty band.
They are not the headline, because 17 annual points cannot carry information about a 2047 that will differ
structurally (EVs, data centres, hydrogen, a maturing economy). Models (all on ln generation, COVID years FY21-22
handled with dummies where the model allows exogenous terms):
  RW-drift   random walk with drift, ARIMA(0,1,0)+c: the pure trend extrapolation
  ARIMA      ARIMA(1,1,0)+c, order chosen by AICc among (p,1,q), p,q <= 1
  ETS-damped Holt's additive trend with damping (statsmodels ETS) - growth fades over time
  ARIMAX     ARIMA(0,1,0) with ln real GDP as exogenous input (GDP path 6.5%/yr): growth-on-growth, the
             closest time-series relative of the headline model
Back-test: fit on FY10-FY19, forecast FY20-FY26 (COVID dummies set at their fitted values), compare with actuals.
Outputs: out/ts_forecasts.csv, out/ts_backtest.csv, out/ts_summary.csv
"""
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
nat = pd.read_csv(D / "national_history.csv").set_index("fy_end_year")
Y = np.log(nat.generation_bu)
GDP = np.log(nat.gdp_cr_2011_12)
H_END = 2047


def covid(idx):
    return pd.DataFrame({"c21": (np.asarray(idx) == 2021).astype(float), "c22": (np.asarray(idx) == 2022).astype(float)}, index=idx)


def fit_forecast(name, y, last, horizon_end, gdp_growth=0.065):
    """Fit on y (index fy_end_year <= last); return mean, lo80, hi80 (TWh) for years last+1..horizon_end."""
    yrs = np.arange(last + 1, horizon_end + 1)
    yy = y.loc[:last]
    ex_in = covid(yy.index)
    ex_out = covid(yrs)
    if name == "RW-drift":
        m = ARIMA(yy, exog=ex_in, order=(0, 1, 0), trend="t").fit()
        f = m.get_forecast(len(yrs), exog=ex_out)
    elif name == "ARIMA":
        best = None
        for p in (0, 1):
            for q in (0, 1):
                try:
                    r = ARIMA(yy, exog=ex_in, order=(p, 1, q), trend="t").fit()
                except Exception:
                    continue
                k = r.df_model + 1; n = r.nobs
                aicc = r.aic + 2 * k * (k + 1) / max(n - k - 1, 1)
                if best is None or aicc < best[0]:
                    best = (aicc, r, (p, 1, q))
        m = best[1]; name = f"ARIMA{best[2]}"
        f = m.get_forecast(len(yrs), exog=ex_out)
    elif name == "ARIMAX":
        g = GDP.loc[:last]
        # future GDP: actual where known (back-test), else 6.5% a year from the last known year
        g_all = GDP.copy()
        for t in yrs:
            if t not in g_all.index or np.isnan(g_all.get(t, np.nan)):
                g_all.loc[t] = g_all.loc[t - 1] + np.log(1 + gdp_growth)
        X_in = pd.concat([ex_in, g.rename("lgdp")], axis=1)
        X_out = pd.concat([ex_out, g_all.loc[yrs].rename("lgdp")], axis=1)
        m = ARIMA(yy, exog=X_in, order=(0, 1, 0), trend="n").fit()
        f = m.get_forecast(len(yrs), exog=X_out)
    elif name == "ETS-damped":
        # ETS has no exogenous terms: COVID years replaced by the average of their neighbours before fitting
        yc = yy.copy()
        if 2021 in yc.index and 2022 in yc.index and 2023 in yc.index:
            step = (yc[2023] - yc[2020]) / 3
            yc[2021], yc[2022] = yc[2020] + step, yc[2020] + 2 * step
        elif 2021 in yc.index and 2022 not in yc.index:
            yc = yc.drop(2021)
        m = ETSModel(pd.Series(yc.values, index=pd.RangeIndex(len(yc))), error="add", trend="add", damped_trend=True).fit(disp=False)
        sim = m.simulate(anchor="end", nsimulations=len(yrs), repetitions=2000, random_errors="bootstrap", random_state=2047)
        mean = m.forecast(len(yrs)).values
        lo, hi = np.percentile(sim.values, 10, axis=1), np.percentile(sim.values, 90, axis=1)
        return name, pd.DataFrame({"mean": np.exp(mean), "lo80": np.exp(lo), "hi80": np.exp(hi)}, index=yrs)
    ci = f.conf_int(alpha=0.2)
    return name, pd.DataFrame({"mean": np.exp(f.predicted_mean.values), "lo80": np.exp(ci.iloc[:, 0].values),
                               "hi80": np.exp(ci.iloc[:, 1].values)}, index=yrs)


MODELS = ["ARIMA", "ETS-damped", "ARIMAX"]  # ARIMA search includes the random walk with drift (0,1,0)

if __name__ == "__main__":
    rows, bt = [], []
    for nm in MODELS:
        label, fc = fit_forecast(nm, Y, 2026, H_END)
        for t, r in fc.iterrows():
            rows.append({"model": label, "fy_end": t, **r.round(1).to_dict()})
        _, b = fit_forecast(nm, Y, 2019, 2026)
        for t in (2024, 2025, 2026):
            bt.append({"model": label, "fy_end": t, "forecast": round(b.loc[t, "mean"], 1), "actual": nat.generation_bu[t],
                       "error_pct": round((b.loc[t, "mean"] / nat.generation_bu[t] - 1) * 100, 1)})
    fc = pd.DataFrame(rows); bt = pd.DataFrame(bt)
    fc.to_csv(OUT / "ts_forecasts.csv", index=False); bt.to_csv(OUT / "ts_backtest.csv", index=False)
    # headline structural model, same back-test (from test_demand outputs) for comparison
    summ = fc[fc.fy_end == H_END][["model", "mean", "lo80", "hi80"]].merge(
        bt.groupby("model").error_pct.apply(lambda e: round(e.abs().mean(), 1)).rename("backtest_mae_pct_fy24_26"), on="model")
    summ = summ.rename(columns={"mean": "gen_2047_twh", "lo80": "p10_twh", "hi80": "p90_twh"})
    summ.to_csv(OUT / "ts_summary.csv", index=False)
    print("2047 generation, TWh (80% interval) and back-test MAE FY24-26:\n", summ.to_string(index=False))
    print("\nBack-test detail:\n", bt.pivot(index="model", columns="fy_end", values="error_pct").to_string())
