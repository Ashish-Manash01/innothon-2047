"""State panel: what drives per-capita electricity requirement across Indian states?

    log(kWh per person)_st = a_s + b·log(real GSDP per person)_st + c·urban%_st + d·COVID_t + e_st

a_s = state fixed effect (climate, industry structure, tariffs, everything state-specific and slow-moving).
b   = income elasticity, c = urbanisation semi-elasticity: both identified from changes WITHIN states.

Robustness: (1) drop flagged observations, (2) Huber robust regression, (3) out-of-sample test
(train FY<=2023, predict FY2024-26), (4) gradient-boosting cross-check on the same test split.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"


def interp_series(points: dict, years):
    """points {year: value}; geometric interpolation for population-type series."""
    ys = np.array(sorted(points)); vs = np.log(np.array([points[y] for y in ys]))
    return np.exp(np.interp(years, ys, vs))


def build_panel():
    m = pd.read_csv(D / "state_master.csv")
    e = pd.read_csv(D / "state_energy_requirement.csv")
    g = pd.read_csv(D / "state_gsdp.csv")
    e = e[~e.code.str.startswith("ISTS")].copy()
    # DVC serves Jharkhand + West Bengal: split 50/50 (assumption, tested below)
    dvc = e[e.code == "DVC"]
    for c in ("JH", "WB"):
        add = dvc.set_index("fy_end_year").requirement_mu / 2
        e.loc[e.code == c, "requirement_mu"] += e.loc[e.code == c, "fy_end_year"].map(add).fillna(0).values
    e = e[e.code != "DVC"]
    # Ladakh energy is reported inside J&K -> add Ladakh population to J&K
    m.loc[m.code == "JK", ["pop_2011_k", "pop_2021_k", "pop_2026_k", "pop_2031_k", "pop_2036_k"]] += \
        m.loc[m.code == "LA", ["pop_2011_k", "pop_2021_k", "pop_2026_k", "pop_2031_k", "pop_2036_k"]].values
    rows = []
    for r in e.itertuples():
        mm = m[m.code == r.code]
        if mm.empty:
            continue
        mm = mm.iloc[0]
        yr = r.fy_end_year - 1  # FY (t-1)-(t) aligned with 1 July of year t-1
        pop = interp_series({2011: mm.pop_2011_k, 2021: mm.pop_2021_k, 2026: mm.pop_2026_k,
                             2031: mm.pop_2031_k, 2036: mm.pop_2036_k}, [yr])[0]
        urb = np.interp(yr, [2011, 2021, 2026, 2031, 2036], [mm.urban_2011_pct, mm.urban_2021_pct,
                        mm.urban_2026_pct, mm.urban_2031_pct, mm.urban_2036_pct])
        gs = g[(g.code == r.code) & (g.fy_end_year == r.fy_end_year)].gsdp_cr_2011_12
        rows.append({"code": r.code, "region": r.cea_region, "fy": r.fy_end_year, "req_mu": r.requirement_mu,
                     "pop_k": pop, "urban": urb, "gsdp": gs.iloc[0] if len(gs) else np.nan, "flag": r.flag})
    p = pd.DataFrame(rows)
    p["kwh_pc"] = p.req_mu * 1000 / p.pop_k
    p["gsdp_pc"] = p.gsdp * 1e7 / (p.pop_k * 1e3)  # ₹ per person (2011-12 prices)
    p["ln_kwh"] = np.log(p.kwh_pc); p["ln_inc"] = np.log(p.gsdp_pc)
    p["covid"] = (p.fy == 2021).astype(int)
    # Exclusions: no GSDP (DN, LD, AN-island grid), Telangana split years, Bangladesh-export year
    p["use"] = p.gsdp.notna() & ~p.code.isin(["DN", "LD", "AN"])
    p.loc[p.code.isin(["AP", "TG"]) & (p.fy <= 2015), "use"] = False
    p.loc[p.flag.fillna("").str.startswith("EXCLUDE"), "use"] = False
    return p


FORM = "ln_kwh ~ ln_inc + urban + covid + C(code)"


def fit(df, robust=False):
    if robust:
        y, X = df.ln_kwh, pd.get_dummies(df[["ln_inc", "urban", "covid", "code"]], columns=["code"], drop_first=True, dtype=float)
        return sm.RLM(y, sm.add_constant(X), M=sm.robust.norms.HuberT()).fit()
    return smf.ols(FORM, data=df).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.code)[0]})


if __name__ == "__main__":
    p = build_panel()
    use = p[p.use].copy()
    p.to_csv(ROOT / "out" / "panel_data.csv", index=False)
    print(f"Panel: {use.code.nunique()} states x {use.fy.nunique()} years = {len(use)} observations")

    res = {}
    m1 = fit(use); res["1 Main (state FE, clustered SE)"] = m1
    clean = use[~use.flag.fillna("").str.contains("step change|drought")]
    res["2 Drop flagged (Odisha FY22+, Karnataka FY24)"] = fit(clean)
    res["3 Huber robust"] = fit(use, robust=True)
    res["4 DVC excluded (JH, WB dropped)"] = fit(use[~use.code.isin(["JH", "WB"])])
    rows = []
    for k, m in res.items():
        se = m.bse
        rows.append({"spec": k, "income_elasticity_b": m.params["ln_inc"], "se_b": se["ln_inc"],
                     "urban_semi_elast_c": m.params["urban"], "se_c": se["urban"], "n": int(m.nobs)})
    tab = pd.DataFrame(rows).round(4)
    print(tab.to_string(index=False))
    print(f"Main model R2 (within+FE) = {m1.rsquared:.3f}")

    # ---------- out-of-sample: train FY<=2023, predict FY2024-26
    tr, te = use[use.fy <= 2023], use[use.fy >= 2024]
    te = te[te.code.isin(tr.code.unique())]
    mt = fit(tr)
    pred_fe = mt.predict(te)
    rmse_fe = np.sqrt(np.mean((np.exp(pred_fe) - te.kwh_pc) ** 2 / te.kwh_pc ** 2)) * 100
    from sklearn.ensemble import GradientBoostingRegressor
    Xcols = ["ln_inc", "urban", "covid"]
    code_mean = tr.groupby("code").ln_kwh.mean()  # state level as a feature (target encoding from TRAIN only)
    Xtr = tr[Xcols].assign(state_lvl=tr.code.map(code_mean)); Xte = te[Xcols].assign(state_lvl=te.code.map(code_mean))
    gbm = GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0).fit(Xtr, tr.ln_kwh)
    pred_g = gbm.predict(Xte)
    rmse_g = np.sqrt(np.mean((np.exp(pred_g) - te.kwh_pc) ** 2 / te.kwh_pc ** 2)) * 100
    # naive: last observed per-capita value carried forward
    last = tr.sort_values("fy").groupby("code").kwh_pc.last()
    rmse_naive = np.sqrt(np.mean((te.code.map(last) - te.kwh_pc) ** 2 / te.kwh_pc ** 2)) * 100
    oos = pd.DataFrame({"model": ["State-FE regression", "Gradient boosting", "Naive (last value)"],
                        "oos_rmse_pct_FY24_26": [rmse_fe, rmse_g, rmse_naive]}).round(2)
    print("\nOut-of-sample error, FY2024-26 (% of actual, RMS):\n", oos.to_string(index=False))
    tab.to_csv(ROOT / "out" / "panel_coefficients.csv", index=False)
    oos.to_csv(ROOT / "out" / "panel_oos.csv", index=False)
    fe = pd.Series({c: m1.params.get(f"C(code)[T.{c}]", 0.0) for c in use.code.unique()})
    fe.to_csv(ROOT / "out" / "panel_state_effects.csv", header=["fixed_effect"])
