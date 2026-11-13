"""INNOTHON demand model v2: GENERATION-ONLY forecast of India's electricity production requirement to FY2046-47
("2047"), national and for the five CEA regions.

The problem statement requires energy GENERATED as the only basis for forecasting and comparison (no installed
capacity, no consumption). Every quantity fitted or compared here is therefore generation (or an inter-regional
energy flow, which is generation moved between regions):

  1. Elasticity of generation per person to real GDP per person, estimated on national generation FY2010-11 to
     FY2025-26 (MoP / CEA), growth-on-growth with COVID dummies. A levels regression is reported as a cross-check.
  2. Regional production requirement = generation in the region + net inter-regional imports (+ Bhutan imports
     to the Eastern region). This is the energy that had to be generated for each region. Shares averaged
     FY2023-24 to FY2025-26 (NPP / CEA generation reports; Grid-India inter-regional exchange).
  3. Projection by region: requirement per person grows with the region's real GSDP per person at the estimated
     elasticity (maturing to k x b by 2047), x population (UN WPP 2024 total; MoHFW state shares). Drivers
     come from the official INNOTHON dataset (state population and GSDP) and MoSPI, aggregated to CEA regions.
  4. New loads absent from history (EVs, data centres, green hydrogen; optional heat + cooking electrification)
     are added bottom-up, converted to generation with a delivery factor (losses + auxiliary use).
Outputs: out/v2_*.csv
"""
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
BASE_FY, T_FY = 2026, 2047
YEARS = np.arange(BASE_FY, 2049)  # fy_end years
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]

nat = pd.read_csv(D / "national_history.csv").set_index("fy_end_year")
un = pd.read_csv(D / "un_wpp2024_projection.csv").set_index("year")
loads = pd.read_csv(D / "new_loads.csv")
master = pd.read_csv(D / "state_master.csv")
gsdp = pd.read_csv(D / "state_gsdp.csv")
REGION = dict(zip(master.code, master.cea_region))


def L(load, param, which="base"):
    return float(loads[(loads.load == load) & (loads.param == param)][which].iloc[0])


# ---------------------------------------------------------------- 1. elasticity on national GENERATION
def fit_national():
    n = nat.loc[2010:BASE_FY].copy()
    n["lg"] = np.log(n.generation_bu * 1e3 / n.population_mn)        # kWh generated per person
    n["ly"] = np.log(n.gdp_cr_2011_12 / n.population_mn)             # real GDP per person
    n["covid"] = (n.index == 2021).astype(int); n["rebound"] = (n.index == 2022).astype(int)
    fd = n[["lg", "ly"]].diff().join(n[["covid", "rebound"]]).dropna()
    m_fd = sm.OLS(fd.lg, fd[["ly", "covid", "rebound"]]).fit()        # growth-on-growth, no drift term
    lv = n.loc[2016:]                                                 # post-shortage years (cross-check)
    m_lv = sm.OLS(lv.lg, sm.add_constant(lv[["ly", "covid"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    m_u = sm.OLS(fd.lg, fd[["ly", "covid", "rebound"]].join(n.urban_pct_un.diff())).fit()
    return n, m_fd, m_lv, m_u


NAT, M_FD, M_LV, M_U = fit_national()
B_HAT, B_SE = float(M_FD.params["ly"]), float(M_FD.bse["ly"])
B_LEVELS, B_LEVELS_SE = float(M_LV.params["ly"]), float(M_LV.bse["ly"])
C_HAT = 0.0  # urbanisation adds nothing significant beyond income (coef 0.07/pp, SE 0.08, p 0.40); kept as a lever
C_TEST, C_SE = float(M_U.params["urban_pct_un"]), float(M_U.bse["urban_pct_un"])

# Weather-smoothed FY26 national generation: FY23 actual (a normal year) carried forward with the model's predicted
# growth for FY24-26, averaged with the actual FY26 so that a cool, wet FY26 (+1.0%) does not set the base level.
_pred = NAT.lg.loc[2023] + (M_FD.params["ly"] * NAT.ly.diff()).loc[2024:2026].sum()
G26_TREND = float(np.exp(_pred) * NAT.population_mn.loc[2026] / 1e3)       # TWh
G26_ACTUAL = float(NAT.generation_bu.loc[2026])
G26 = 0.5 * (G26_TREND + G26_ACTUAL)

# ---------------------------------------------------------------- 2. regional production requirement (generation basis)
gen_hist = pd.read_csv(D / "region_generation_history.csv")
flows = pd.read_csv(D / "region_net_import_history.csv")
bhutan = pd.read_csv(D / "bhutan_import_history.csv").set_index("fy_end_year").bhutan_mu


def regional_requirement():
    g = gen_hist.pivot(index="fy_end_year", columns="cea_region", values="generation_mu")
    f = flows.pivot(index="fy_end_year", columns="cea_region", values="net_import_mu")
    yrs = sorted(set(g.index) & set(f.index))
    need = g.loc[yrs, REG] + f.loc[yrs, REG].fillna(0)
    need["Eastern"] += bhutan.reindex(yrs).values
    need = need.div(need.sum(axis=1), axis=0).mul(g.loc[yrs, REG].sum(axis=1) + bhutan.reindex(yrs).values, axis=0)
    return need, g.loc[yrs, REG], f.loc[yrs, REG]


NEED, GEN_R, FLOW_R = regional_requirement()
SHARE26 = NEED.loc[2024:2026].sum() / NEED.loc[2024:2026].sum().sum()

# ---------------------------------------------------------------- 3. regional drivers
un_years = np.array(sorted(un.index)); un_pop = un.population_mn.reindex(un_years).values
def un_total(cal_year, scale=1.0):
    return float(np.exp(np.interp(cal_year, un_years, np.log(un_pop)))) * 1e3 * scale  # thousand

mm = master.set_index("code").copy()
popcols = ["pop_2026_k", "pop_2031_k", "pop_2036_k"]
mm.loc["JK", popcols] = mm.loc["JK", popcols].values + mm.loc["LA", popcols].values
mm = mm.drop(index="LA")
sh = mm[popcols].div(mm[popcols].sum())
sh_trend = (np.log(sh.pop_2036_k) - np.log(sh.pop_2031_k)) / 5


@lru_cache(maxsize=None)
def pop_share(cal_year):
    if cal_year <= 2036:
        out = pd.Series({c: np.exp(np.interp(cal_year, [2026, 2031, 2036], np.log([sh.loc[c, k] for k in popcols]))) for c in sh.index})
    else:
        out = sh.pop_2036_k * np.exp(sh_trend * (cal_year - 2036))
    return out / out.sum()


@lru_cache(maxsize=None)
def region_pop_share(cal_year):
    return pop_share(cal_year).groupby(REGION).sum().reindex(REG)


_MI = master.set_index("code")
@lru_cache(maxsize=None)
def urban_region(cal_year):
    def u(c):
        r = _MI.loc[c]
        v = np.interp(cal_year, [2021, 2026, 2031, 2036], [r.urban_2021_pct, r.urban_2026_pct, r.urban_2031_pct, r.urban_2036_pct])
        if cal_year > 2036:
            v = r.urban_2036_pct + (r.urban_2036_pct - r.urban_2031_pct) / 5 * (cal_year - 2036)
        return min(v, 100.0)
    ps = pop_share(cal_year)
    s = pd.Series({c: u(c) for c in ps.index}) * ps
    return (s.groupby(REGION).sum() / ps.groupby(REGION).sum()).reindex(REG)


# Regional GSDP shares: FY25 level, drifting at the FY15-FY25 trend, damped to zero by 2047
gp = gsdp.pivot(index="code", columns="fy_end_year", values="gsdp_cr_2011_12")
g25 = gp[2025].dropna(); g15 = gp[2015].reindex(g25.index)
_rg25 = g25.groupby(REGION).sum().reindex(REG); _rg15 = g15.groupby(REGION).sum().reindex(REG)
RSHARE25 = _rg25 / _rg25.sum()
RDRIFT = (np.log(_rg25 / _rg25.sum()) - np.log(_rg15 / _rg15.sum())) / 10


# ---------------------------------------------------------------- 4. one scenario run
def run(p, detail=False):
    gdp_path = {BASE_FY: 1.0}
    for t in YEARS[1:]:
        gdp_path[t] = gdp_path[t - 1] * (1 + p["gdp"])
    pop_scale = p["pop_2047"] / (un_total(2046) / 1e3)
    f_now = p.get("factor_now", 1.12)
    natl, rows = [], []
    need = SHARE26 * G26 * p.get("base_scale", 1.0)          # TWh, FY26 regional requirement
    prev = None; gshare = RSHARE25.copy()
    for t in YEARS:
        cal = t - 1
        frac = min(max((t - BASE_FY) / (T_FY - BASE_FY), 0), 1)
        tot_pop = un_total(cal) * (1 + (pop_scale - 1) * frac)
        pop_r = region_pop_share(cal) * tot_pop
        damp = max(0.0, 1 - (t - BASE_FY) / (T_FY - BASE_FY))
        if prev is not None:
            gshare = gshare * np.exp(RDRIFT * damp); gshare = gshare / gshare.sum()
        gsdp_r = gshare * gdp_path[t]
        urb = urban_region(cal)
        if prev is not None:
            b_t = p["b"] * (1 - (1 - p["k"]) * frac)
            inc_g = np.log((gsdp_r / pop_r) / (prev["gsdp"] / prev["pop"]))
            need = need * (pop_r / prev["pop"]) * np.exp(b_t * inc_g + p.get("c", 0.0) * (urb - prev["urb"]))
        organic = float(need.sum())
        organic0 = float((SHARE26 * G26 * p.get("base_scale", 1.0)).sum())
        # ---- new loads (end-use TWh) -> generation with the delivery factor
        sig = lambda y: 1 / (1 + np.exp(-0.35 * (y - 2039)))
        adopt = (sig(t) - sig(BASE_FY)) / (sig(T_FY) - sig(BASE_FY))
        ev47 = p["ev_twh_2047"]
        ev = 4.0 + (ev47 - 4.0) * max(adopt, 0) if t <= T_FY else ev47 * 1.03 ** (t - T_FY)
        ev_add = ev - 4.0 * organic / organic0              # the part already inside the historical trend is removed
        y = t - 1
        if y <= 2040:
            dc = 10.0 * (p["dc_twh_2040"] / 10.0) ** ((y - 2025) / 15)
        else:
            dc = p["dc_twh_2040"] * (p["dc_twh_2047"] / p["dc_twh_2040"]) ** ((min(y, 2046) - 2040) / 6) * 1.03 ** max(y - 2046, 0)
        dc_add = dc - 10.0 * organic / organic0
        h2_mt = p["h2_mt_2047"] * max(adopt, 0) if t <= T_FY else p["h2_mt_2047"] * (1 + 0.04 * (t - T_FY))
        h2_twh = h2_mt * p["kwh_per_kg"]
        heat = p.get("heat_twh_2047", 0.0) * max(adopt, 0) if t <= T_FY else p.get("heat_twh_2047", 0.0) * 1.027 ** (t - T_FY)
        cook = p.get("cook_twh_2047", 0.0) * max(adopt, 0) if t <= T_FY else p.get("cook_twh_2047", 0.0) * 1.01 ** (t - T_FY)
        f_t = f_now + (p["bridge_2047"] - f_now) * frac     # generation per unit of new end-use load
        natl.append({"fy_end": t, "pop_mn": tot_pop / 1e3, "gen_organic": organic, "organic_req_twh": organic,
                     "ev_twh": ev, "dc_twh": dc, "h2_mt": h2_mt, "h2_twh": h2_twh, "bridge": f_t,
                     "gen_ev_dc": max(ev_add + dc_add, 0) * f_t, "gen_h2": h2_twh * 1.02,
                     "heat_twh": heat, "cook_twh": cook, "gen_elec": (heat + cook) * f_t})
        if detail:
            for r in REG:
                rows.append({"fy_end": t, "region": r, "organic_twh": need[r], "pop_k": pop_r[r], "gsdp_index": gsdp_r[r],
                             "urban": urb[r], "kwh_gen_pc": need[r] * 1e9 / (pop_r[r] * 1e3)})
        prev = {"gsdp": gsdp_r, "pop": pop_r, "urb": urb}
    n = pd.DataFrame(natl).set_index("fy_end")
    n["gen_grid"] = n.gen_organic + n.gen_ev_dc + n.gen_elec
    n["gen_total"] = n.gen_grid + n.gen_h2
    return (n, pd.DataFrame(rows)) if detail else n


def elec_2047(which):
    return L("elec_heat", "consumption_2047_twh", which), L("elec_cook", "consumption_2047_twh", which)


def ev_2047(which):
    tot = 0.0
    for v in ["two_wheelers", "cars", "three_wheelers", "buses", "trucks"]:
        tot += L("ev", f"{v}_stock_2047", which) * 1e6 * L("ev", f"{v}_ev_share", which) * L("ev", f"{v}_kwh_per_vehicle", which)
    return tot / 1e9


_common = dict(c=C_HAT, factor_now=1.12)
SCEN = {
    "Low":  dict(_common, gdp=0.055, pop_2047=1600, b=B_HAT - B_SE, k=0.60, bridge_2047=1.08, ev_twh_2047=ev_2047("low"),
                 dc_twh_2040=100.0, dc_twh_2047=L("datacentre", "consumption_2047_twh", "low"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt", "low"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg", "low")),
    "Base": dict(_common, gdp=0.065, pop_2047=1665, b=B_HAT, k=0.75, bridge_2047=1.10, ev_twh_2047=ev_2047("base"),
                 dc_twh_2040=191.0, dc_twh_2047=L("datacentre", "consumption_2047_twh"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg")),
    "High": dict(_common, gdp=0.075, pop_2047=1720, b=B_HAT + B_SE, k=0.90, bridge_2047=1.14, ev_twh_2047=ev_2047("high"),
                 dc_twh_2040=260.0, dc_twh_2047=L("datacentre", "consumption_2047_twh", "high"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt", "high"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg", "high")),
}

if __name__ == "__main__":
    print(f"Elasticity (growth-on-growth, FY11-26): b = {B_HAT:.3f} (SE {B_SE:.3f}); levels FY16-26 cross-check {B_LEVELS:.3f} (SE {B_LEVELS_SE:.3f})")
    print(f"Urbanisation added to growth model: coef {M_U.params['urban_pct_un']:.4f} (SE {M_U.bse['urban_pct_un']:.4f}, p {M_U.pvalues['urban_pct_un']:.2f})")
    print(f"FY26 base: actual {G26_ACTUAL:.0f}, trend {G26_TREND:.0f}, used {G26:.0f} TWh")
    print("Regional requirement shares (FY24-26):", SHARE26.round(4).to_dict())
    res = {}
    for k, p in SCEN.items():
        n, st = run(p, detail=True); res[k] = n
        n.to_csv(OUT / f"v2_national_{k.lower()}.csv")
        if k == "Base":
            st.to_csv(OUT / "v2_regions_base.csv", index=False)
    summ = pd.DataFrame({k: v.loc[T_FY, ["pop_mn", "gen_organic", "gen_ev_dc", "gen_grid", "h2_mt", "gen_h2", "gen_total"]] for k, v in res.items()}).T
    summ["cagr_total_pct"] = ((summ.gen_total / G26_ACTUAL) ** (1 / 21) - 1) * 100
    print(summ.round(1).to_string()); summ.round(2).to_csv(OUT / "v2_summary_2047.csv")
    pd.DataFrame({"generation": GEN_R.stack(), "net_import": FLOW_R.stack(), "requirement": NEED.stack()}).round(0).to_csv(OUT / "v2_regional_requirement_history.csv")
    coef = pd.DataFrame([("b growth-on-growth FY11-26", B_HAT, B_SE), ("b levels FY16-26", B_LEVELS, B_LEVELS_SE),
                         ("urbanisation (per pp, added)", float(M_U.params["urban_pct_un"]), float(M_U.bse["urban_pct_un"]))],
                        columns=["term", "estimate", "se"]).round(4)
    coef.to_csv(OUT / "v2_coefficients.csv", index=False)
