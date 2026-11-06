"""INNOTHON demand model v1 — state-level, driver-based projection of India's electricity GENERATION
requirement to FY2046-47 ("2047"), with new loads, scenarios, Monte Carlo and regional roll-up.

Layers
  1. ORGANIC demand (36 states): per-capita requirement grows with real income per capita at the panel-estimated
     elasticity (declining over time as demand matures) + urbanisation term; x population (UN total, state shares
     from MoHFW projections). Base level = weather-smoothed FY26 (fitted + mean residual FY24-26).
  2. NEW LOADS absent from history: EVs (bottom-up fleet), data centres, green hydrogen (kept as a separate layer).
  3. Requirement -> GENERATION via the empirical bridge (1.077 today, falling as low-auxiliary RE grows).
Outputs: out/v1_*.csv, out/v1_*.png
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
from functools import lru_cache
sys.path.insert(0, str(Path(__file__).parent))
from panel import build_panel, fit

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; OUT = ROOT / "out"
BASE_FY, T_FY = 2026, 2047
YEARS = np.arange(BASE_FY, 2049)  # fy_end years

# ---------------------------------------------------------------- inputs
panel = build_panel(); use = panel[panel.use]
M = fit(use)
B_HAT, C_HAT = M.params["ln_inc"], M.params["urban"]
B_SE, C_SE = M.bse["ln_inc"], M.bse["urban"]
use = use.assign(resid=M.resid)
master = pd.read_csv(D / "state_master.csv")
gsdp = pd.read_csv(D / "state_gsdp.csv")
nat = pd.read_csv(D / "national_history.csv").set_index("fy_end_year")
un = pd.read_csv(D / "un_wpp2024_projection.csv").set_index("year")
loads = pd.read_csv(D / "new_loads.csv")
energy = pd.read_csv(D / "state_energy_requirement.csv")
REGION = dict(zip(master.code, master.cea_region))


def L(load, param, which="base"):
    v = loads[(loads.load == load) & (loads.param == param)][which].iloc[0]
    return float(v)


# UN population path (calendar July), FY t <- July t-1
un_years = np.array(sorted(un.index)); un_pop = un.population_mn.reindex(un_years).values
def un_total(cal_year, scale=1.0):
    return float(np.exp(np.interp(cal_year, un_years, np.log(un_pop)))) * 1e3 * scale  # thousand

# ---------------------------------------------------------------- state base year (FY26)
state_codes = [c for c in use.code.unique()]
last = panel[panel.fy == BASE_FY].set_index("code").loc[state_codes].copy()
# States that have not yet released FY26 GSDP: FY25 GSDP grown at the national FY26 real growth rate
gs25 = panel[panel.fy == 2025].set_index("code").gsdp
miss = last.gsdp.isna()
last.loc[miss, "gsdp"] = gs25.reindex(last.index[miss]) * (1 + nat.loc[2026, "real_gdp_growth_pct"] / 100)
last["gsdp_pc"] = last.gsdp * 1e7 / (last.pop_k * 1e3); last["ln_inc"] = np.log(last.gsdp_pc); last["covid"] = 0
fitted26 = pd.Series(np.asarray(M.predict(last.reset_index())), index=state_codes)
assert fitted26.notna().all(), "base-year fit has gaps"
res_recent = use[use.fy >= 2024].groupby("code").resid.mean()
smoothed_ln_tg = fitted26 + res_recent.reindex(state_codes).fillna(0)        # weather-smoothed, per TG person
smoothed_req_mu = np.exp(smoothed_ln_tg) * last.pop_k / 1000                  # MU, FY26 level
_ACTUAL26_MU = last.req_mu                                                    # for the check below

# Population shares (MoHFW TG), all 36 entities; J&K includes Ladakh (energy reported jointly)
mm = master.set_index("code").copy()
popcols = ["pop_2026_k", "pop_2031_k", "pop_2036_k"]
mm.loc["JK", popcols] = mm.loc["JK", popcols].values + mm.loc["LA", popcols].values
mm = mm.drop(index="LA")
sh = mm[popcols].div(mm[popcols].sum())
sh_trend = (np.log(sh.pop_2036_k) - np.log(sh.pop_2031_k)) / 5
@lru_cache(maxsize=None)
def pop_share(cal_year):
    if cal_year <= 2036:
        out = pd.Series({c: np.exp(np.interp(cal_year, [2026, 2031, 2036],
                         np.log([sh.loc[c, k] for k in popcols]))) for c in sh.index})
    else:
        out = sh.pop_2036_k * np.exp(sh_trend * (cal_year - 2036))
    return out / out.sum()

# Re-base per-capita levels onto the PROJECTION population (UN total x TG shares) so that the base year
# reproduces the weather-smoothed FY26 requirement exactly.
pop_proj26 = pop_share(BASE_FY - 1).reindex(state_codes) * un_total(BASE_FY - 1)
base_ln_kwh = np.log(smoothed_req_mu * 1000 / pop_proj26)

_MI = master.set_index("code")
@lru_cache(maxsize=None)
def urban_path(code, cal_year):
    r = _MI.loc[code]
    u = np.interp(cal_year, [2021, 2026, 2031, 2036], [r.urban_2021_pct, r.urban_2026_pct, r.urban_2031_pct, r.urban_2036_pct])
    if cal_year > 2036:
        u = r.urban_2036_pct + (r.urban_2036_pct - r.urban_2031_pct) / 5 * (cal_year - 2036)
    return min(u, 100.0)

_DU = {y: pd.Series({c: urban_path(c, y) - urban_path(c, y - 1) for c in state_codes}) for y in range(2025, 2050)}

# GSDP shares and drift (damped to zero by 2047)
gp = gsdp.pivot(index="code", columns="fy_end_year", values="gsdp_cr_2011_12")
g25 = gp[2025].dropna(); g15 = gp[2015].reindex(g25.index)
share25 = g25 / g25.sum()
drift = ((np.log(g25 / g25.sum()) - np.log(g15 / g15.sum())) / 10).fillna(0)

# FY26 actual requirement for entities outside the panel (DN, LD, AN) and ISTS residual
e26 = energy[energy.fy_end_year == BASE_FY].set_index("code").requirement_mu
other_mu = e26.reindex(["DN", "LD", "AN"]).fillna(0)
ists_mu = e26[e26.index.str.startswith("ISTS")].sum()
bridge_now = pd.read_csv(D / "generation_requirement_bridge.csv", index_col=0).loc[2022:2026, "gen_over_req"].mean()


_PS0 = None
def _consts():
    global _PS0
    if _PS0 is None:
        ps0 = pop_share(BASE_FY - 1); tot0 = un_total(BASE_FY - 1)
        pop0_states = ps0.reindex(state_codes) * tot0
        req0_states = (np.exp(base_ln_kwh) * pop0_states / 1000)
        _PS0 = dict(pc0=req0_states.sum() / pop0_states.sum(), req0=req0_states.sum(),
                    pop0_other=(ps0.reindex(other_mu.index).fillna(0) * tot0))
    return _PS0

# ---------------------------------------------------------------- one scenario run
def run(p, detail=False):
    """p: dict of parameters. Returns dict with national series and (optionally) state detail."""
    yrs = YEARS
    gdp_path = {BASE_FY: 1.0}
    for t in yrs[1:]:
        gdp_path[t] = gdp_path[t - 1] * (1 + p["gdp"])
    pop_scale = p["pop_2047"] / (un_total(2046) / 1e3)  # scale UN path so July-2046 matches scenario
    rows, natl = [], []
    ln_pc = base_ln_kwh.copy()
    prev = None
    for t in yrs:
        cal = t - 1
        frac = min(max((t - BASE_FY) / (T_FY - BASE_FY), 0), 1)
        tot_pop = un_total(cal) * (1 + (pop_scale - 1) * frac)
        ps = pop_share(cal)
        pop_t = ps * tot_pop
        damp = max(0.0, 1 - (t - BASE_FY) / (T_FY - BASE_FY))
        if prev is None:
            gshare = share25.copy()
        else:
            gshare = prev["gshare"] * np.exp(drift.reindex(prev["gshare"].index).fillna(0) * damp)
            gshare = gshare / gshare.sum()
        gsdp_t = gshare * gdp_path[t]
        if prev is not None:
            b_t = p["b"] * (1 - (1 - p["k"]) * frac)
            inc_g = np.log((gsdp_t / pop_t.reindex(gsdp_t.index)) / (prev["gsdp"] / prev["pop"].reindex(prev["gsdp"].index)))
            du = _DU[cal]
            ln_pc = ln_pc + b_t * inc_g.reindex(state_codes).fillna(inc_g.mean()) + p["c"] * du
        req_states_mu = np.exp(ln_pc) * pop_t.reindex(state_codes) / 1000  # MU
        # per-capita growth index for entities without GSDP (follow national average per-capita change)
        K = _consts()
        pc_index = (req_states_mu.sum() / pop_t.reindex(state_codes).sum()) / K["pc0"]
        other = other_mu * pc_index * (pop_t.reindex(other_mu.index).fillna(0) / K["pop0_other"]).replace([np.inf, np.nan], 1)
        organic_mu = req_states_mu.sum() + other.sum()
        ists = ists_mu * organic_mu / (K["req0"] + other_mu.sum())
        organic_mu += ists
        # ---- new loads (consumption, TWh)
        # Adoption S-curve centred 2039, slope 0.35 -> calibrated so EV demand passes ~27 TWh in FY31 and ~38 TWh
        # in FY32 (IEA STEPS ~25 TWh 2030; IESA/CEA ~38 TWh FY2031-32).
        sig = lambda y: 1 / (1 + np.exp(-0.35 * (y - 2039)))
        adopt = (sig(t) - sig(BASE_FY)) / (sig(T_FY) - sig(BASE_FY))
        ev47 = p["ev_twh_2047"]
        ev = 4.0 + (ev47 - 4.0) * max(adopt, 0) if t <= T_FY else ev47 * 1.03 ** (t - T_FY)
        ev_add = ev - 4.0 * organic_mu / organic0_mu  # remove the part already inside the organic trend
        # Data centres: Wood Mackenzie path 10 TWh (2025) -> DC_2040 (base 191), then to DC_2047
        y = t - 1
        if y <= 2040:
            dc = 10.0 * (p["dc_twh_2040"] / 10.0) ** ((y - 2025) / 15)
        else:
            dc = p["dc_twh_2040"] * (p["dc_twh_2047"] / p["dc_twh_2040"]) ** ((min(y, 2046) - 2040) / 6) * 1.03 ** max(y - 2046, 0)
        dc_add = dc - 10.0 * organic_mu / organic0_mu
        h2_mt = p["h2_mt_2047"] * max(adopt, 0) if t <= T_FY else p["h2_mt_2047"] * (1 + 0.04 * (t - T_FY))
        h2_twh = h2_mt * p["kwh_per_kg"]  # Mt * kWh/kg = TWh
        # Optional ELECTRIFICATION layer (low-temperature industrial heat + induction cooking): policy-driven fuel
        # switching beyond the historical trend. Same adoption S-curve as EVs. Default 0 -> headline unchanged.
        heat = p.get("heat_twh_2047", 0.0) * max(adopt, 0) if t <= T_FY else p.get("heat_twh_2047", 0.0) * 1.027 ** (t - T_FY)
        cook = p.get("cook_twh_2047", 0.0) * max(adopt, 0) if t <= T_FY else p.get("cook_twh_2047", 0.0) * 1.01 ** (t - T_FY)
        bridge_t = bridge_now + (p["bridge_2047"] - bridge_now) * frac
        organic_twh = organic_mu / 1e3
        natl.append({"fy_end": t, "pop_mn": tot_pop / 1e3, "organic_req_twh": organic_twh, "ev_twh": ev, "dc_twh": dc,
                     "h2_mt": h2_mt, "h2_twh": h2_twh, "bridge": bridge_t,
                     "gen_organic": organic_twh * bridge_t, "gen_ev_dc": max(ev_add + dc_add, 0) * bridge_t,
                     "gen_h2": h2_twh * 1.02, "heat_twh": heat, "cook_twh": cook,
                     "gen_elec": (heat + cook) * bridge_t})
        if detail:
            for c in state_codes:
                rows.append({"fy_end": t, "code": c, "req_twh": req_states_mu[c] / 1e3, "pop_k": pop_t[c],
                             "kwh_pc": np.exp(ln_pc[c]), "gsdp_cr": gsdp_t.get(c, np.nan), "urban": urban_path(c, cal)})
            for c, v in other.items():
                rows.append({"fy_end": t, "code": c, "req_twh": v / 1e3, "pop_k": pop_t.get(c, np.nan)})
            rows.append({"fy_end": t, "code": "ISTS", "req_twh": ists / 1e3})
        prev = {"gsdp": gsdp_t, "pop": pop_t, "gshare": gshare}
    n = pd.DataFrame(natl).set_index("fy_end")
    n["gen_grid"] = n.gen_organic + n.gen_ev_dc + n.gen_elec
    n["gen_total"] = n.gen_grid + n.gen_h2
    return (n, pd.DataFrame(rows)) if detail else n


organic0_mu = ((np.exp(base_ln_kwh) * pop_share(BASE_FY - 1).reindex(state_codes) * un_total(BASE_FY - 1) / 1000).sum()
               + other_mu.sum() + ists_mu)


def elec_2047(which):
    """(industrial heat, cooking) consumption in 2047, TWh, for low/base/high."""
    return L("elec_heat", "consumption_2047_twh", which), L("elec_cook", "consumption_2047_twh", which)


def ev_2047(which):
    tot = 0.0
    for v in ["two_wheelers", "cars", "three_wheelers", "buses", "trucks"]:
        tot += L("ev", f"{v}_stock_2047", which) * 1e6 * L("ev", f"{v}_ev_share", which) * L("ev", f"{v}_kwh_per_vehicle", which)
    return tot / 1e9  # TWh


SCEN = {
    "Low":  dict(gdp=0.055, pop_2047=1600, b=0.62, k=0.60, c=C_HAT, bridge_2047=1.045, ev_twh_2047=ev_2047("low"),
                 dc_twh_2040=100.0, dc_twh_2047=L("datacentre", "consumption_2047_twh", "low"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt", "low"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg", "low")),
    "Base": dict(gdp=0.065, pop_2047=1665, b=B_HAT, k=0.75, c=C_HAT, bridge_2047=1.06, ev_twh_2047=ev_2047("base"),
                 dc_twh_2040=191.0, dc_twh_2047=L("datacentre", "consumption_2047_twh"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg")),
    "High": dict(gdp=0.075, pop_2047=1720, b=0.85, k=0.90, c=C_HAT, bridge_2047=1.075, ev_twh_2047=ev_2047("high"),
                 dc_twh_2040=260.0, dc_twh_2047=L("datacentre", "consumption_2047_twh", "high"), h2_mt_2047=L("hydrogen", "green_h2_2047_mt", "high"),
                 kwh_per_kg=L("hydrogen", "electrolysis_kwh_per_kg", "high")),
}

if __name__ == "__main__":
    print(f"Panel: b = {B_HAT:.3f} (se {B_SE:.3f}), c_urban = {C_HAT:.4f} (se {C_SE:.4f}); bridge now = {bridge_now:.4f}")
    print(f"EV 2047 consumption (TWh): low {ev_2047('low'):.0f}, base {ev_2047('base'):.0f}, high {ev_2047('high'):.0f}")
    results, base_states = {}, None
    for k, p in SCEN.items():
        if k == "Base":
            n, st = run(p, detail=True); base_states = st
        else:
            n = run(p)
        results[k] = n
    summ = pd.DataFrame({k: v.loc[T_FY, ["pop_mn", "organic_req_twh", "gen_organic", "gen_ev_dc", "gen_grid", "h2_mt",
                                          "gen_h2", "gen_total"]] for k, v in results.items()}).T.round(1)
    summ["cagr_grid_pct"] = (((summ.gen_grid / 1847.913) ** (1 / 21) - 1) * 100).round(2)
    summ["cagr_total_pct"] = (((summ.gen_total / 1847.913) ** (1 / 21) - 1) * 100).round(2)
    print("\nFY2046-47 (TWh generated unless noted):\n", summ.to_string())
    b = results["Base"]
    print("\nBase path checks: FY27 organic requirement = {:.0f} TWh (CEA LGBR FY27 forecast 1,887 TWh); "
          "EV FY31 = {:.0f} / FY32 = {:.0f} TWh (IEA ~25 in 2030, IESA ~38 FY32); DC 2030 = {:.0f}, 2040 = {:.0f} TWh (S&P 57; WoodMac 191)".format(
          b.loc[2027, "organic_req_twh"], b.loc[2031, "ev_twh"], b.loc[2032, "ev_twh"], b.loc[2031, "dc_twh"], b.loc[2041, "dc_twh"]))
    print("FY2047-48 (calendar 2047 end): grid {:.0f}, total {:.0f} TWh".format(b.loc[2048, "gen_grid"], b.loc[2048, "gen_total"]))
    for k, v in results.items():
        v.to_csv(OUT / f"v1_national_{k.lower()}.csv")
    summ.to_csv(OUT / "v1_summary_2047.csv")
    base_states.to_csv(OUT / "v1_states_base.csv", index=False)
