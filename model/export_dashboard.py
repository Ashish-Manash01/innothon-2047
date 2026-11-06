"""Export every dataset the dashboard reads into out/dash/ (CSV), with one row per scenario x year x region.

Grids are FULL model runs (no interpolation):
  demand grid  : GDP {5.5..7.5%} x income elasticity {0.62, 0.689, 0.85} x EV {low, base, high}
                 x data centres {low, base, high} x green H2 {5, 12, 25 Mt}  = 405 runs, national path FY26-FY47
                 + regional split at FY30/35/40/47.
  mix grid     : CO2 cap {0.8, 1.0, 1.2, 1.45, 1.7 Gt} x nuclear policy {<=50 GW, least-cost <=100, Mission =100}
                 x RE build speed {-25%, base, +25%} x demand {P10, Base, P90} = 135 LP runs (2047, by region).
"""
import itertools, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_v1 as dm
import mix_lp as M
from regional import regional

OUT = dm.OUT / "dash"; OUT.mkdir(exist_ok=True)
L = dm.L


def demand_grid():
    base = dm.SCEN["Base"]
    GDP = [0.055, 0.060, 0.065, 0.070, 0.075]
    B = {"low": 0.62, "base": float(dm.B_HAT), "high": 0.85}
    EV = {k: dm.ev_2047(k) for k in ("low", "base", "high")}
    DC = {"low": (100.0, L("datacentre", "consumption_2047_twh", "low")), "base": (191.0, L("datacentre", "consumption_2047_twh")),
          "high": (260.0, L("datacentre", "consumption_2047_twh", "high"))}
    H2 = {"low": 5.0, "base": 12.0, "high": 25.0}
    paths, regs, t0 = [], [], time.time()
    for gdp, bk, ek, dk, hk in itertools.product(GDP, B, EV, DC, H2):
        p = dict(base, gdp=gdp, b=B[bk], ev_twh_2047=EV[ek], dc_twh_2040=DC[dk][0], dc_twh_2047=DC[dk][1], h2_mt_2047=H2[hk])
        sid = f"g{gdp*1000:.0f}_b{bk}_ev{ek}_dc{dk}_h2{hk}"
        r, n = regional(p, [2030, 2035, 2040, 2047])
        for y in range(2026, 2048):
            paths.append({"scenario": sid, "gdp_pct": round(gdp * 100, 1), "elasticity": bk, "ev": ek, "dc": dk, "h2": hk,
                          "fy_end": y, "gen_organic": n.loc[y, "gen_organic"], "gen_ev_dc": n.loc[y, "gen_ev_dc"],
                          "gen_h2": n.loc[y, "gen_h2"], "gen_grid": n.loc[y, "gen_grid"], "gen_total": n.loc[y, "gen_total"],
                          "pop_mn": n.loc[y, "pop_mn"]})
        r = r.assign(scenario=sid)
        regs.append(r[["scenario", "fy_end", "region", "gen_grid_twh", "gen_h2_twh", "gen_total_twh"]])
    P = pd.DataFrame(paths).round(2); R = pd.concat(regs).round(2)
    print(f"demand grid: {P.scenario.nunique()} runs in {time.time()-t0:.0f}s")
    # sanity: the base cell reproduces the published base run
    b = P[(P.scenario == "g65_bbase_evbase_dcbase_h2base") & (P.fy_end == 2047)].gen_total.iloc[0]
    ref = pd.read_csv(dm.OUT / "v1_national_base.csv", index_col=0).loc[2047, "gen_total"]
    assert abs(b - ref) < 0.5, (b, ref)
    P.to_csv(OUT / "demand_paths.csv", index=False); R.to_csv(OUT / "demand_regional.csv", index=False)


def mix_grid():
    rows, summ, t0 = [], [], time.time()
    CO2 = [800, 1000, 1200, 1450, 1700]
    NUC = {"delay50": dict(nuclear_cap=50), "leastcost": dict(), "mission100": dict(nuclear_floor=100)}
    RE = {"slow": 0.75, "base": 1.0, "fast": 1.25}
    DEM = ["P10", "base", "P90"]
    for co2, nk, rk, dk in itertools.product(CO2, NUC, RE, DEM):
        kw = dict(NUC[nk]); kw.update(co2_cap=co2, demand=dk, solar_cap=M.A.solar_cap_2047_gw * RE[rk], wind_cap=M.A.wind_cap_2047_gw * RE[rk])
        o = M.solve(label="", **kw)
        sid = f"co2{co2}_{nk}_re{rk}_d{dk}"
        S = M.summarise(o)
        G, C = o["gen"], o["cap"]
        for r in M.REG:
            for s in M.SRC:
                rows.append({"scenario": sid, "region": r, "source": s, "twh": G.loc[r, s], "gw": C.loc[r, s]})
        net = G.sum(axis=1) - o["demand"]
        summ.append({"scenario": sid, "co2_cap_mt": co2, "nuclear": nk, "re_build": rk, "demand": dk,
                     "total_twh": G.sum().sum(), "co2_mt": o["co2"], "co2_over_cap_mt": o["co2_excess"], "unserved_twh": o["unserved"],
                     "non_fossil_pct": S["non_fossil_%"], "cost_rs_per_kwh": S["cost_rs_per_kwh"],
                     "co2_shadow_rs_per_t": S["co2_shadow_rs_per_t"], "bess_gw": o["bess"].sum(), "psp_gw": o["psp"].sum(),
                     **{"net_export_" + r.lower().replace("-", "_"): net[r] for r in M.REG}})
    print(f"mix grid: {len(summ)} LP runs in {time.time()-t0:.0f}s")
    pd.DataFrame(rows).round(2).to_csv(OUT / "mix_grid_regional.csv", index=False)
    pd.DataFrame(summ).round(2).to_csv(OUT / "mix_grid_summary.csv", index=False)


def static():
    h = pd.read_csv(dm.D / "national_history.csv")
    h[["fy", "fy_end_year", "generation_bu", "population_mn", "urban_pct_un", "gdp_cr_2011_12"]].rename(
        columns={"fy_end_year": "fy_end", "generation_bu": "generation_twh"}).to_csv(OUT / "history_national.csv", index=False)
    a = pd.read_csv(dm.D / "region_generation_fy26.csv")
    a.rename(columns={"coal_lignite": "coal"}).melt(id_vars="cea_region", var_name="source", value_name="twh") \
        .rename(columns={"cea_region": "region"}).to_csv(OUT / "fy26_regional_mix.csv", index=False)
    mc = pd.read_csv(dm.OUT / "v1_montecarlo.csv")
    q = []
    for y in (2031, 2036, 2041, 2047):
        for c in ("gen_grid", "gen_total"):
            v = mc[f"{c}_{y}"].quantile([.1, .5, .9]).values
            q.append({"fy_end": y, "measure": c, "p10": v[0], "p50": v[1], "p90": v[2]})
    base26 = pd.read_csv(dm.OUT / "v1_national_base.csv", index_col=0).loc[2026]
    for c in ("gen_grid", "gen_total"):
        q.append({"fy_end": 2026, "measure": c, "p10": base26[c], "p50": base26[c], "p90": base26[c]})
    pd.DataFrame(q).sort_values(["measure", "fy_end"]).round(0).to_csv(OUT / "mc_fan.csv", index=False)
    pd.read_csv(dm.OUT / "v1_tornado.csv").to_csv(OUT / "tornado.csv", index=False)
    pd.read_csv(dm.OUT / "backcast_fy26.csv").to_csv(OUT / "backcast_fy26.csv", index=False)
    pd.read_csv(dm.OUT / "mix_verification_base.csv")[["check", "pass", "detail"]].to_csv(OUT / "verification_checks.csv", index=False)
    pd.read_csv(dm.OUT / "pathway_national.csv").to_csv(OUT / "pathway_national.csv", index=False)
    pd.read_csv(dm.OUT / "pathway_regional.csv").to_csv(OUT / "pathway_regional.csv", index=False)
    # resources vs what the base plan uses
    res = pd.read_csv(dm.D / "state_resources.csv").groupby("cea_region").agg(
        solar_potential_gw=("solar_potential_gwp", "sum"), wind_potential_gw=("wind150_potential_gw", "sum"),
        hydro_potential_gw=("hydro_exploitable_mw", "sum"))
    res["solar_potential_gw"] = res.solar_potential_gw / 1.25; res["hydro_potential_gw"] = res.hydro_potential_gw / 1e3
    cap = pd.read_csv(dm.OUT / "mix_base_capacity_gw.csv", index_col=0)
    res = res.join(cap[["solar", "wind", "hydro"]].rename(columns=lambda c: f"{c}_used_2047_gw"))
    res.index.name = "region"; res.round(1).to_csv(OUT / "resources_vs_use.csv")
    # panel model coefficients (trace)
    pd.read_csv(dm.OUT / "panel_coefficients.csv").to_csv(OUT / "panel_coefficients.csv", index=False)


def benchmarks():
    rows = [
        ("Total generation 2047 (TWh)", "This model, base", 5553, "Demand model v1"),
        ("Total generation 2047 (TWh)", "This model, Monte Carlo P10", 5217, "2,000 runs"),
        ("Total generation 2047 (TWh)", "This model, Monte Carlo P90", 6828, "2,000 runs"),
        ("Total generation 2047 (TWh)", "Published 2047 scenarios, low", 5254, "Range cited by IFPEN"),
        ("Total generation 2047 (TWh)", "Published 2047 scenarios, high", 6033, "Range cited by IFPEN"),
        ("Energy requirement 2031-32 (TWh)", "This model, FY32 requirement", None, "Demand model v1"),
        ("Energy requirement 2031-32 (TWh)", "CEA NEP 2022-32", 2473.8, "NEP Vol-I, 20th EPS"),
        ("Energy requirement 2026-27 (TWh)", "This model, FY27 requirement", None, "Demand model v1"),
        ("Energy requirement 2026-27 (TWh)", "CEA LGBR forecast", 1887, "CEA LGBR 2026-27"),
        ("Solar 2047 (GW)", "This model, base", 1279, "Mix model"), ("Solar 2047 (GW)", "CEA indicative 2047", 1200, "Down To Earth, 2026"),
        ("Wind 2047 (GW)", "This model, base", 375, "Mix model"), ("Wind 2047 (GW)", "CEA indicative 2047 (low end)", 400, "Down To Earth, 2026"),
        ("Nuclear 2047 (GW)", "This model, base", 83, "Mix model"), ("Nuclear 2047 (GW)", "Nuclear Energy Mission", 100, "Govt target"),
        ("Storage 2047 (GW)", "This model, base (BESS+PSP)", 503, "Mix model"), ("Storage 2047 (GW)", "CEA storage need 2046-47", 476, "CEA PSP roadmap, Jan 2026"),
        ("Coal share FY32 / FY30 (%)", "This model, FY30", None, "Pathway"), ("Coal share FY32 / FY30 (%)", "CEA NEP, FY32", 50, "NEP 2022-32 via ORF"),
        ("Power CO2 FY32 / FY30 (Mt)", "This model, FY30", None, "Pathway"), ("Power CO2 FY32 / FY30 (Mt)", "CEA draft NEP, FY32", 1180, "Draft NEP 2022"),
    ]
    B = pd.DataFrame(rows, columns=["metric", "estimate", "value", "source"])
    n = pd.read_csv(dm.OUT / "v1_national_base.csv", index_col=0)
    P = pd.read_csv(dm.OUT / "pathway_national.csv").set_index("fy_end")
    B.loc[B.estimate == "This model, FY32 requirement", "value"] = round(n.loc[2032, "organic_req_twh"] + n.loc[2032, "gen_ev_dc"] / n.loc[2032, "bridge"], 1)
    B.loc[B.estimate == "This model, FY27 requirement", "value"] = round(n.loc[2027, "organic_req_twh"], 1)
    B.loc[(B.metric.str.startswith("Coal share")) & (B.estimate == "This model, FY30"), "value"] = round(P.loc[2030, "coal_pct"], 1)
    B.loc[(B.metric.str.startswith("Power CO2")) & (B.estimate == "This model, FY30"), "value"] = round(P.loc[2030, "co2_mt"], 0)
    B.to_csv(OUT / "benchmarks.csv", index=False)


def assumptions():
    a = pd.read_csv(dm.D / "mix_assumptions.csv").assign(model="mix")
    l = pd.read_csv(dm.D / "new_loads.csv").rename(columns={"param": "item", "base": "value", "unit": "unit", "source_or_basis": "basis"})
    l["item"] = l.load + ": " + l["item"]; l = l[["item", "value", "unit", "basis"]].assign(model="demand (new loads)")
    d = pd.DataFrame([
        ("Income elasticity b (panel FE)", round(float(dm.B_HAT), 3), "-", f"State fixed-effects panel, 32 states x 11 yrs, SE {dm.B_SE:.3f}", "demand"),
        ("Urbanisation coefficient c", round(float(dm.C_HAT), 4), "per pp", f"Same panel, SE {dm.C_SE:.4f} (not significant; income absorbs it)", "demand"),
        ("Elasticity decay k (b falls to k*b by 2047)", 0.75, "-", "Maturing demand; realised FY18-26 elasticity 0.694", "demand"),
        ("GDP growth (real, base)", 6.5, "%/yr", "Scenario 5.5-7.5%", "demand"),
        ("Population 2047", 1665, "million", "UN WPP 2024 medium variant", "demand"),
        ("Generation / requirement bridge 2047", 1.06, "ratio", "FY22-26 mean 1.077, falling as RE has low auxiliary use", "demand"),
        ("Base year FY26 (weather-smoothed)", 1916, "TWh gen", "Fitted + mean residual FY24-26 (+4.2% vs actual hot/cool-year noise)", "demand"),
    ], columns=["item", "value", "unit", "basis", "model"])
    pd.concat([d, l, a]).to_csv(OUT / "assumptions.csv", index=False)


def sources():
    S = [("CEA", "Generation by source & region, installed capacity, energy requirement (states), transfer capacity", "https://cea.nic.in"),
         ("Ministry of Power / PIB", "National generation history, FY26 totals, coal pipeline", "https://pib.gov.in"),
         ("UN World Population Prospects 2024", "Population 2010-2050", "https://population.un.org/wpp/"),
         ("MoHFW Technical Group on Population Projections", "State population shares 2011-2036", "https://mohfw.gov.in"),
         ("NIUA / Census", "State urbanisation", "https://niua.in"),
         ("MoSPI / RBI Handbook", "GDP & GSDP at 2011-12 prices", "https://mospi.gov.in"),
         ("NISE / MNRE", "Solar potential (wasteland-based, 2025)", "https://mnre.gov.in"),
         ("NIWE", "Wind potential at 150 m", "https://niwe.res.in"),
         ("CEA hydro status / PSP roadmap", "Hydro & pumped-storage potential and pipeline", "https://cea.nic.in"),
         ("DAE / NPCIL (Parliament replies)", "Nuclear sites and status", "https://dae.gov.in"),
         ("MNRE", "Record solar/wind additions FY26; RE generation by state", "https://mnre.gov.in"),
         ("IEA, IESA, Wood Mackenzie, IRADe, NITI-RMI", "EV, data-centre and green-hydrogen calibration", "see SOURCES.md"),
         ("CEA NEP 2022-32; CEA indicative 2047 mix", "Benchmarks", "https://cea.nic.in")]
    pd.DataFrame(S, columns=["source", "used_for", "link"]).to_csv(OUT / "sources.csv", index=False)


if __name__ == "__main__":
    static(); benchmarks(); assumptions(); sources()
    demand_grid(); mix_grid()
    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:28s} {f.stat().st_size/1024:8.1f} KB  rows={sum(1 for _ in open(f))-1}")
