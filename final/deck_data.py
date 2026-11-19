"""Collect every number the final 7-slide deck shows from out/, so the deck always matches the models."""
import json
from pathlib import Path
import pandas as pd

R = Path(__file__).resolve().parents[1]; O = R / "out"
nb = pd.read_csv(O / "v2_national_base.csv", index_col=0)
h = pd.read_csv(R / "data" / "national_history.csv").set_index("fy_end_year")
q = pd.read_csv(O / "v2_mc_quantiles_2047.csv", index_col=0)
sc = pd.read_csv(O / "mix_scenarios_2047.csv").set_index("scenario")
P = pd.read_csv(O / "pathway_national.csv").set_index("fy_end")
g = pd.read_csv(O / "mix_base_generation_twh.csv", index_col=0)
bal = pd.read_csv(O / "mix_base_regional_balance.csv", index_col=0)
cap = pd.read_csv(O / "mix_base_capacity_gw.csv", index_col=0)
ts = pd.read_csv(O / "ts_summary.csv").set_index("model")
tsf = pd.read_csv(O / "ts_forecasts.csv")
tor = pd.read_csv(O / "v2_tornado.csv")
ml = pd.read_csv(O / "ml_summary.csv").set_index("model")
coef = pd.read_csv(O / "v2_coefficients.csv").set_index("term")
bk = pd.read_csv(O / "backcast_fy26.csv"); bk = bk[bk.region == "India"].set_index("source")
tests = pd.read_csv(O / "v2_tests.csv").set_index("test")
rg = pd.read_csv(O / "v2_regional_2047_base.csv", index_col=0)
SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
B = sc.loc["Base"]

# back-test MAE of the structural model, from the test detail string "...errors FY24: +0.7%, FY25: +1.0%, FY26: +6.2%"
det = tests.loc[[t for t in tests.index if t.startswith("Back-test")][0], "detail"].split("errors ")[-1]
errs = [abs(float(x.split(": ")[1].rstrip("%"))) for x in det.split(", ")]
arima = [m for m in ts.index if m.startswith("ARIMA(")][0]
bk_share = (bk.model_twh / bk.model_twh.sum() - bk.actual_twh / bk.actual_twh.sum()).abs().max() * 100

ROLE = {"Northern": "Solar hub (Rajasthan) + Himalayan hydro; exports",
        "Western": "Solar, coastal wind, pithead coal; exports",
        "Southern": "Wind + nuclear firm a weaker sun; imports a little",
        "Eastern": "Weak sun, no wind: coal + new nuclear; imports",
        "North-Eastern": "Hydro; exports"}
regs = []
for r in ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]:
    net = bal.loc[r, "net_export_twh"]
    regs.append({"name": r, "gen": {k: round(float(g.loc[r, k]), 1) for k in SRC}, "total": float(bal.loc[r, "generation_twh"]),
                 "need": float(bal.loc[r, "demand_twh"]), "role": ROLE[r] + f" ({'+' if net >= 0 else '−'}{abs(net):,.0f} TWh)"})

years = list(range(2010, 2048))
D = dict(
    total=float(nb.loc[2047, "gen_total"]), fy26=float(h.generation_bu[2026]), p10=float(q.loc["gen_total_2047", "P10"]),
    p90=float(q.loc["gen_total_2047", "P90"]), cagr=((nb.loc[2047, "gen_total"] / h.generation_bu[2026]) ** (1 / 21) - 1) * 100,
    nonfossil=float(B["non_fossil_%"]), cost=float(B.cost_rs_per_kwh), co2=float(B.co2_mt), bess=float(B.bess_gw),
    solar_gw=float(B.solar_gw), wind_gw=float(B.wind_gw), nuc_gw=float(B.nuclear_gw),
    mix={k: float(B[f"{k}_%"]) for k in SRC}, h2=float(nb.loc[2047, "gen_h2"]), h2_mt=round(float(nb.loc[2047, "h2_mt"]), 0),
    b=float(coef.loc["b growth-on-growth FY11-26", "estimate"]), b_se=float(coef.loc["b growth-on-growth FY11-26", "se"]),
    years=years, hist={y: float(h.generation_bu[y]) for y in h.index},
    fc_total={y: round(float(nb.loc[y, "gen_total"])) for y in range(2026, 2048)},
    fc_grid={y: round(float(nb.loc[y, "gen_grid"])) for y in range(2026, 2048)},
    ts={"arima": {int(r.fy_end): float(r["mean"]) for _, r in tsf[tsf.model == arima].iterrows()}},
    ts_sum={"ARIMA": {"v": float(ts.loc[arima, "gen_2047_twh"]), "e": float(ts.loc[arima, "backtest_mae_pct_fy24_26"])},
            "ARIMAX": {"v": float(ts.loc["ARIMAX", "gen_2047_twh"]), "e": float(ts.loc["ARIMAX", "backtest_mae_pct_fy24_26"])},
            "ETS": {"v": float(ts.loc["ETS-damped", "gen_2047_twh"]), "e": float(ts.loc["ETS-damped", "backtest_mae_pct_fy24_26"])}},
    ml={k: {"v": float(ml.loc[k, "gen_2047_twh"]), "e": float(ml.loc[k, "backtest_mae_pct_fy24_26"])}
        for k in ["Gradient boosting", "Random forest", "Neural network (MLP)", "Random forest (levels)"]},
    bt_struct=sum(errs) / len(errs), regions=regs, south_x=float(rg.loc["Southern", "growth_x"]),
    pathway=[{"label": ("FY26 actual" if y == 2026 else f"FY{str(y)[2:]}"), **{k: float(P.loc[y, f"{k}_twh"]) for k in SRC},
              "nf": float(P.loc[y, "non_fossil_pct"]), "coal_pct": float(P.loc[y, "coal_pct"]), "co2": float(P.loc[y, "co2_mt"])} for y in P.index],
    tornado=[{"label": r.driver, "low": float(r.low), "high": float(r.high)} for _, r in tor.sort_values("span").iterrows()],
    scen=[{"name": n, "nf": float(sc.loc[k, "non_fossil_%"]), "co2": float(sc.loc[k, "co2_mt"]), "over": float(sc.loc[k, "co2_over_cap_mt"]),
           "cost": float(sc.loc[k, "cost_rs_per_kwh"])} for n, k in [
        ("Base: 1.2 Gt cap", "Base"), ("CO₂ cap 1.7 Gt (draft-NEP-like)", "Relaxed CO2 (1.7 Gt)"), ("CO₂ cap 0.8 Gt", "Strict CO2 (0.8 Gt)"),
        ("Nuclear ≤ 50 GW", "Nuclear delay (<=50 GW)"), ("Solar & wind 25% faster", "Faster RE build (+25%)"),
        ("Solar & wind 25% slower", "Slower RE build (-25%)"), ("Demand at P90", "Demand P90"), ("Solar 30% dearer", "Solar cost +30%")]],
    slow_over=float(sc.loc["Slower RE build (-25%)", "co2_over_cap_mt"]), nuc_over=float(sc.loc["Nuclear delay (<=50 GW)", "co2_over_cap_mt"]),
    backcast_err=float(bk_share), fy30_coal=float(P.loc[2030, "coal_pct"]), fy30_co2=float(P.loc[2030, "co2_mt"]),
    app="https://innothon-2047-lht5kj3587q6dwmteapysu.streamlit.app/", app_short="innothon-2047…streamlit.app",
    repo="https://github.com/Ashish-Manash01/innothon-2047", repo_short="github.com/Ashish-Manash01/innothon-2047",
)
json.dump(D, open(Path(__file__).parent / "deck_data.json", "w"), indent=1, ensure_ascii=False)
print({k: D[k] for k in ["total", "p10", "p90", "nonfossil", "cost", "bt_struct", "backcast_err", "fy30_coal"]})
