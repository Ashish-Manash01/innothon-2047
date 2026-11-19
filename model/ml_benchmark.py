"""Machine-learning benchmark on national electricity GENERATION (MoP/CEA, FY2009-10 to FY2025-26).

Question it answers: would machine learning forecast 2047 better than our explainable model?
Same data, same back-test as model/timeseries.py and model/test_demand.py:
  fit on FY11-FY19, predict FY20-FY26 recursively with actual GDP and population, score FY24-FY26.

Two framings, because they fail in instructive ways:
  LEVELS  target ln(kWh generated per person), features ln(real GDP per person), urban share.
          Tree models (random forest, gradient boosting) cannot predict outside the values they were trained on,
          so their forecast flattens as soon as income passes the FY19 level. This is shown, not hidden.
  GROWTH  target yearly growth of ln generation, features GDP growth, population growth, COVID flags.
          Any model can project growth, so this is the fair comparison. Models: gradient boosting, random forest,
          a small neural network (MLP), and ridge regression as the linear reference.
For 2047 the growth models are run forward with the base-case GDP (6.5%/yr) and UN population path, then
compared with our model's grid-only figure (history contains no green hydrogen). Permutation importance shows
what the best ML model relies on. 16 yearly observations is very little data for ML; that is the point.
Outputs: out/ml_backtest.csv, out/ml_summary.csv, out/ml_forecasts.csv, out/ml_importance.csv
"""
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
SEED = 2047
n = pd.read_csv(D / "national_history.csv").set_index("fy_end_year")
un = pd.read_csv(D / "un_wpp2024_projection.csv").set_index("year")
base = pd.read_csv(OUT / "v2_national_base.csv", index_col=0)

n["lg"] = np.log(n.generation_bu); n["lgpc"] = np.log(n.generation_bu * 1e3 / n.population_mn)
n["lypc"] = np.log(n.gdp_cr_2011_12 / n.population_mn)
n["g_gen"] = n.lg.diff(); n["g_gdp"] = np.log(n.gdp_cr_2011_12).diff(); n["g_pop"] = np.log(n.population_mn).diff()
n["covid"] = (n.index == 2021).astype(float); n["rebound"] = (n.index == 2022).astype(float)
GF = ["g_gdp", "g_pop", "covid", "rebound"]
LF = ["lypc", "urban_pct_un"]


def growth_models():
    return {
        "Gradient boosting": GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=SEED),
        "Random forest": RandomForestRegressor(n_estimators=500, min_samples_leaf=2, random_state=SEED),
        "Neural network (MLP)": make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(8,), alpha=1.0, max_iter=20000, random_state=SEED)),
        "Ridge (linear reference)": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    }


def recursive_path(model, start_year, start_lg, feats):
    """feats: DataFrame of growth features indexed by year > start_year; returns ln generation path."""
    lg, out = start_lg, {}
    for t, row in feats.iterrows():
        lg = lg + float(model.predict(row[GF].to_frame().T)[0]); out[t] = lg
    return pd.Series(out)


def future_features(last=2026, end=2047, gdp=0.065):
    yrs = np.arange(last + 1, end + 1)
    pop = np.exp(np.interp(yrs - 1, un.index.values, np.log(un.population_mn.values)))  # FY t uses July of year t-1
    pop_prev = np.exp(np.interp(yrs - 2, un.index.values, np.log(un.population_mn.values)))
    return pd.DataFrame({"g_gdp": np.log(1 + gdp), "g_pop": np.log(pop / pop_prev), "covid": 0.0, "rebound": 0.0}, index=yrs)


if __name__ == "__main__":
    tr = n.loc[2011:2019].dropna(subset=["g_gen"]); full = n.loc[2011:2026]
    bt, fc, summ = [], [], []
    # ---- growth framing
    for name, mdl in growth_models().items():
        mdl.fit(tr[GF], tr.g_gen)
        path = recursive_path(mdl, 2019, n.lg[2019], n.loc[2020:2026, GF])
        errs = {t: (np.exp(path[t]) / n.generation_bu[t] - 1) * 100 for t in (2024, 2025, 2026)}
        for t, e in errs.items():
            bt.append({"model": name, "framing": "growth", "fy_end": t, "forecast": round(float(np.exp(path[t])), 1),
                       "actual": n.generation_bu[t], "error_pct": round(e, 1)})
        mdl.fit(full[GF], full.g_gen)                                     # refit on all years for 2047
        fut = recursive_path(mdl, 2026, n.lg[2026], future_features())
        for t, v in fut.items():
            fc.append({"model": name, "fy_end": int(t), "gen_twh": round(float(np.exp(v)), 1)})
        summ.append({"model": name, "framing": "growth", "gen_2047_twh": round(float(np.exp(fut[2047]))),
                     "backtest_mae_pct_fy24_26": round(np.mean(np.abs(list(errs.values()))), 1)})
    # ---- levels framing (shows the extrapolation failure of trees)
    for name, mdl in {"Random forest (levels)": RandomForestRegressor(n_estimators=500, min_samples_leaf=2, random_state=SEED),
                      "Gradient boosting (levels)": GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, random_state=SEED)}.items():
        mdl.fit(tr[LF], tr.lgpc)
        pred = np.exp(mdl.predict(n.loc[2024:2026, LF])) * n.population_mn.loc[2024:2026] / 1e3
        errs = (pred / n.generation_bu.loc[2024:2026] - 1) * 100
        for t, e in errs.items():
            bt.append({"model": name, "framing": "levels", "fy_end": t, "forecast": round(float(pred[t]), 1), "actual": n.generation_bu[t], "error_pct": round(e, 1)})
        mdl.fit(full[LF], full.lgpc)
        # 2047 inputs: GDP per person at 6.5% GDP growth over UN population; urban share from UN
        pop47 = float(np.exp(np.interp(2046, un.index.values, np.log(un.population_mn.values))))
        gdp47 = n.gdp_cr_2011_12[2026] * 1.065 ** 21
        X47 = pd.DataFrame({"lypc": [np.log(gdp47 / pop47)], "urban_pct_un": [float(np.interp(2046, un.index.values, un.urban_pct.values))]})
        v47 = float(np.exp(mdl.predict(X47)[0]) * pop47 / 1e3)
        summ.append({"model": name, "framing": "levels", "gen_2047_twh": round(v47), "backtest_mae_pct_fy24_26": round(float(errs.abs().mean()), 1)})
    bt, fc, summ = pd.DataFrame(bt), pd.DataFrame(fc), pd.DataFrame(summ)
    # reference rows: our model and its back-test (from test_demand outputs)
    t = pd.read_csv(OUT / "v2_tests.csv").set_index("test")
    det = t.loc[[x for x in t.index if x.startswith("Back-test")][0], "detail"].split("errors ")[-1]
    our_mae = np.mean([abs(float(x.split(": ")[1].rstrip("%"))) for x in det.split(", ")])
    summ = pd.concat([pd.DataFrame([{"model": "Our model (grid only, no H2)", "framing": "structural", "gen_2047_twh": round(float(base.loc[2047, "gen_grid"])),
                                     "backtest_mae_pct_fy24_26": round(our_mae, 1)}]), summ], ignore_index=True)
    # permutation importance of the best growth ML model
    g = summ[(summ.framing == "growth") & ~summ.model.str.startswith("Ridge")].sort_values("backtest_mae_pct_fy24_26").iloc[0].model
    mdl = growth_models()[g].fit(full[GF], full.g_gen)
    pi = permutation_importance(mdl, full[GF], full.g_gen, n_repeats=200, random_state=SEED)
    imp = pd.DataFrame({"model": g, "feature": ["GDP growth", "Population growth", "COVID year (FY21)", "Rebound year (FY22)"],
                        "importance": pi.importances_mean.round(5)}).sort_values("importance", ascending=False)
    bt.to_csv(OUT / "ml_backtest.csv", index=False); fc.to_csv(OUT / "ml_forecasts.csv", index=False)
    summ.to_csv(OUT / "ml_summary.csv", index=False); imp.to_csv(OUT / "ml_importance.csv", index=False)
    print(summ.to_string(index=False)); print("\nBack-test errors (%):\n", bt.pivot_table(index="model", columns="fy_end", values="error_pct").to_string())
    print("\nPermutation importance,", g, ":\n", imp.to_string(index=False))
