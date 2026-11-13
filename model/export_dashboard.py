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
import demand_gen as dm
import mix_lp as M
from regional import regional

OUT = dm.OUT / "dash"; OUT.mkdir(exist_ok=True)
L = dm.L


def demand_grid():
    base = dm.SCEN["Base"]
    GDP = [0.055, 0.060, 0.065, 0.070, 0.075]
    B = {"low": float(dm.B_HAT - dm.B_SE), "base": float(dm.B_HAT), "high": float(dm.B_HAT + dm.B_SE)}
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
    ref = pd.read_csv(dm.OUT / "v2_national_base.csv", index_col=0).loc[2047, "gen_total"]
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
    mc = pd.read_csv(dm.OUT / "v2_montecarlo.csv")
    q = []
    for y in (2031, 2036, 2041, 2047):
        for c in ("gen_grid", "gen_total"):
            v = mc[f"{c}_{y}"].quantile([.1, .5, .9]).values
            q.append({"fy_end": y, "measure": c, "p10": v[0], "p50": v[1], "p90": v[2]})
    base26 = pd.read_csv(dm.OUT / "v2_national_base.csv", index_col=0).loc[2026]
    for c in ("gen_grid", "gen_total"):
        q.append({"fy_end": 2026, "measure": c, "p10": base26[c], "p50": base26[c], "p90": base26[c]})
    pd.DataFrame(q).sort_values(["measure", "fy_end"]).round(0).to_csv(OUT / "mc_fan.csv", index=False)
    pd.read_csv(dm.OUT / "v2_tornado.csv").to_csv(OUT / "tornado.csv", index=False)
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
    # model coefficients and regional requirement history (trace)
    pd.read_csv(dm.OUT / "v2_coefficients.csv").to_csv(OUT / "coefficients.csv", index=False)
    pd.read_csv(dm.OUT / "v2_regional_requirement_history.csv").to_csv(OUT / "regional_requirement_history.csv", index=False)
    pd.read_csv(dm.D / "region_generation_history.csv").to_csv(OUT / "region_generation_history.csv", index=False)


def benchmarks():
    """Generation-only comparisons (the rules forbid comparing on installed capacity or consumption)."""
    n = pd.read_csv(dm.OUT / "v2_national_base.csv", index_col=0)
    q = pd.read_csv(dm.OUT / "v2_mc_quantiles_2047.csv", index_col=0)
    P = pd.read_csv(dm.OUT / "pathway_national.csv").set_index("fy_end")
    t = pd.read_csv(dm.OUT / "v2_tests.csv").set_index("test")
    rows = [
        ("Total generation 2047 (TWh)", "This model, base", round(n.loc[2047, "gen_total"]), "Generation-only demand model"),
        ("Total generation 2047 (TWh)", "This model, Monte Carlo P10", q.loc["gen_total_2047", "P10"], "2,000 runs"),
        ("Total generation 2047 (TWh)", "This model, Monte Carlo P90", q.loc["gen_total_2047", "P90"], "2,000 runs"),
        ("Total generation 2047 (TWh)", "Published 2047 scenarios, low", 5254, "Range cited by IFPEN"),
        ("Total generation 2047 (TWh)", "Published 2047 scenarios, high", 6033, "Range cited by IFPEN"),
        ("Generation FY2025-26 (TWh)", "Actual (MoP)", dm.G26_ACTUAL, "Cool, wet year: +1.0%"),
        ("Generation FY2025-26 (TWh)", "Weather-smoothed base used", round(dm.G26, 1), "Mean of actual and FY23-based trend"),
        ("Generation FY2025-26 (TWh)", "MoP generation programme", 2000.4, "Power Sector at a Glance"),
        ("Back-test FY24-26 (error %)", "Elasticity fitted to FY19 only", t.loc[[x for x in t.index if x.startswith("Back-test")][0], "detail"], "model/test_demand.py"),
        ("Back-test FY24-26 (error %)", "Naive FY12-19 growth carried forward", t.loc[[x for x in t.index if x.startswith("INFO naive")][0], "detail"], "model/test_demand.py"),
        ("Coal share of generation FY30 / FY32 (%)", "This model, FY30", round(P.loc[2030, "coal_pct"], 1), "Pathway"),
        ("Coal share of generation FY30 / FY32 (%)", "CEA NEP, FY32", 50, "NEP 2022-32 via ORF"),
        ("Power CO2 FY30 / FY32 (Mt)", "This model, FY30", round(P.loc[2030, "co2_mt"]), "Pathway"),
        ("Power CO2 FY30 / FY32 (Mt)", "CEA draft NEP, FY32", 1180, "Draft NEP 2022"),
    ]
    pd.DataFrame(rows, columns=["metric", "estimate", "value", "source"]).to_csv(OUT / "benchmarks.csv", index=False)


def assumptions():
    a = pd.read_csv(dm.D / "mix_assumptions.csv").assign(model="mix")
    l = pd.read_csv(dm.D / "new_loads.csv").rename(columns={"param": "item", "base": "value", "unit": "unit", "source_or_basis": "basis"})
    l["item"] = l.load + ": " + l["item"]; l = l[["item", "value", "unit", "basis"]].assign(model="demand (new loads)")
    d = pd.DataFrame([
        ("Income elasticity of generation per person b", round(float(dm.B_HAT), 3), "-", f"National generation FY11-26, growth-on-growth with COVID dummies, SE {dm.B_SE:.3f}; levels FY16-26 {dm.B_LEVELS:.3f}", "demand"),
        ("Urbanisation coefficient c", 0.0, "per pp", f"Tested: {dm.C_TEST:.3f} (SE {dm.C_SE:.3f}), not significant beyond income -> 0", "demand"),
        ("Regional requirement shares (FY24-26)", "; ".join(f"{k} {v:.3f}" for k, v in dm.SHARE26.items()), "share", "Own generation + net inter-regional imports (NPP/CEA, Grid-India)", "demand"),
        ("Elasticity decay k (b falls to k*b by 2047)", 0.75, "-", "Maturing demand; realised FY18-26 elasticity 0.694", "demand"),
        ("GDP growth (real, base)", 6.5, "%/yr", "Scenario 5.5-7.5%", "demand"),
        ("Population 2047", 1665, "million", "UN WPP 2024 medium variant", "demand"),
        ("Delivery factor for new end-use loads 2047", 1.10, "TWh gen per TWh end use", "1.12 today falling to 1.10: T&D losses + auxiliary use (assumption, range 1.08-1.14)", "demand"),
        ("Base year FY26 (weather-smoothed)", round(dm.G26), "TWh gen", f"Mean of actual {dm.G26_ACTUAL:.0f} and FY23-based trend {dm.G26_TREND:.0f}", "demand"),
    ], columns=["item", "value", "unit", "basis", "model"])
    pd.concat([d, l, a]).to_csv(OUT / "assumptions.csv", index=False)


def sources():
    S = [("INNOTHON official dataset (renewable-india-dataset)", "State population and GSDP 2006-2024 (cross-checked against MoSPI; post-2019 GSDP imputed)", "https://github.com/chrisjaimyantony/renewable-india-dataset"),
         ("National Power Portal / CEA 18-column generation reports", "Region-wise conventional generation FY19-FY26", "https://npp.gov.in"),
         ("CEA Monthly RE Generation Reports", "Region-wise RE generation FY19-FY26", "https://cea.nic.in"),
         ("Grid-India (via T&D India)", "Net inter-regional energy exchange FY24-FY26", "https://grid-india.in"),
         ("CEA", "Fleet and transfer capacity as optimiser inputs (not used for forecasting or comparison)", "https://cea.nic.in"),
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
         ("CEA NEP 2022-32; CEA indicative 2047 mix", "Benchmarks", "https://cea.nic.in"),
         ("BEE India Energy Scenario 2023-24", "Final energy 597 Mtoe, industry 49.5% (electrification layer sizing)", "https://beeindia.gov.in"),
         ("IEA Electrification special report (2026)", "Heat <150 C ~30% of India's industrial heat", "https://www.iea.org"),
         ("Energy Innovation, Electrifying Industrial Heat in India", "Electric heat cost-competitive below 200 C", "https://energyinnovation.org"),
         ("The India Forum (A. Shankar, Apr 2026)", "LPG 31 Mt/yr; ~78 kWh replaces one cylinder", "https://www.theindiaforum.in")]
    pd.DataFrame(S, columns=["source", "used_for", "link"]).to_csv(OUT / "sources.csv", index=False)


if __name__ == "__main__":
    static(); benchmarks(); assumptions(); sources()
    demand_grid(); mix_grid()
    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:28s} {f.stat().st_size/1024:8.1f} KB  rows={sum(1 for _ in open(f))-1}")
