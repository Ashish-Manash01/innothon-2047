"""India 2047 Electricity Generation Forecast — interactive dashboard (ExxonMobil INNOTHON 2026).

Run locally:  streamlit run streamlit_app.py
Every number is computed live by the project's own models:
  model/demand_gen.py generation-only demand model  model/regional.py  roll-up to CEA regions
  model/mix_lp.py     least-cost regional mix (LP)  model/pathway.py   FY30/35/40/47 milestones
Metric throughout: electricity GENERATED (TWh), FY2046-47.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "model"))

st.set_page_config(page_title="India 2047 Electricity Forecast", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
import viz
viz.setup()

SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
LAB = dict(coal="Coal", gas="Natural gas", nuclear="Nuclear", hydro="Hydro", solar="Solar", wind="Wind", bess="Batteries", psp="Pumped storage")
COL = viz.COL
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
REGCOL = viz.REGCOL
OUT = ROOT / "out"; DATA = ROOT / "data"
fmt0 = lambda v: f"{v:,.0f}"


# ------------------------------------------------------------------ models (cached)
@st.cache_resource(show_spinner="Loading models and fitting the generation model…")
def models():
    import demand_gen as dm
    import mix_lp as M
    import regional as R
    import pathway as PW
    import run_mix as RM
    return dm, M, R, PW, RM


dm, M, R, PW, RM = models()


def params_key(p):
    return tuple(sorted((k, round(float(v), 6)) for k, v in p.items()))


@st.cache_data(show_spinner=False)
def run_demand(key):
    p = dict(key)
    nb, stt = dm.run(p, detail=True)
    reg, _ = R.regional(p, list(range(2026, 2048)))
    return nb, stt, reg


@st.cache_data(show_spinner=False)
def run_mix(dkey, co2, nuc_cap, nuc_floor, re_mult, tx, sto_mult, solar_mult):
    nb, stt, reg = run_demand(dkey)
    d = reg[reg.fy_end == 2047].set_index("region")
    o = M.solve(co2_cap=co2, nuclear_cap=nuc_cap, nuclear_floor=nuc_floor, tx_mult=tx, storage_cost_mult=sto_mult,
                solar_cost_mult=solar_mult, solar_cap=M.A.solar_cap_2047_gw * re_mult, wind_cap=M.A.wind_cap_2047_gw * re_mult,
                dem=(d.gen_grid_twh, d.gen_h2_twh), label="live")
    if o["status"] != "Optimal":
        return {"status": o["status"]}
    checks = RM.verify(o)
    keep = {k: o[k] for k in ["status", "gen", "cap", "gen_slices", "storage", "bess", "psp", "flows", "co2", "cost_cr", "demand",
                              "grid", "h2", "peak", "co2_excess", "unserved", "co2_dual"]}
    keep["summary"] = M.summarise(o); keep["checks"] = checks
    return keep


@st.cache_data(show_spinner=False)
def run_pathway(dkey):
    res = PW.run_path(dict(dkey))
    rows = []
    for y, o in res.items():
        G = o["gen"]
        rows.append({"fy_end": y, **{s: G[s].sum() for s in SRC}, "co2_mt": o["co2"], "co2_cap": PW.CO2[y],
                     **{f"{s}_gw": o["cap"][s].sum() for s in SRC}, "bess_gw": o["bess"].sum(),
                     "unserved": o["unserved"], "over_cap": o["co2_excess"]})
        for r in REG:
            for s in SRC:
                rows[-1][f"{r}|{s}"] = G.loc[r, s]
    return pd.DataFrame(rows).set_index("fy_end")


@st.cache_data
def csv(name, folder="out"):
    return pd.read_csv((OUT if folder == "out" else DATA) / name)


hist = csv("national_history.csv", "data").set_index("fy_end_year")
states = csv("state_master.csv", "data")
fy26_reg = csv("region_generation_fy26.csv", "data").set_index("cea_region")
mcq = csv("v2_mc_quantiles_2047.csv").set_index("Unnamed: 0")
mc = csv("v2_montecarlo.csv")

# ------------------------------------------------------------------ sidebar: demand assumptions
st.sidebar.title("Demand assumptions")
st.sidebar.caption("Every change re-runs the generation demand model, the regional split, the optimiser and the pathway. All forecasting uses energy generated only.")
base = dm.SCEN["Base"]
EV = {"Slow": dm.ev_2047("low"), "Base": dm.ev_2047("base"), "Fast": dm.ev_2047("high")}
ELEC = {"Off": (0.0, 0.0), "Low": dm.elec_2047("low"), "Base": dm.elec_2047("base"), "High": dm.elec_2047("high")}


def reset():
    for k, v in dict(gdp=6.5, b=round(float(dm.B_HAT), 3), k=0.75, pop=1665, ev="Base", dc=250, h2=12.0, bridge=1.10, elec="Off").items():
        st.session_state[k] = v


if "gdp" not in st.session_state:
    reset()
gdp = st.sidebar.slider("Real GDP growth, % a year", 4.5, 8.5, key="gdp", step=0.1)
b = st.sidebar.slider("Income elasticity of electricity use", 0.50, 1.00, key="b", step=0.01,
                      format="%.3f", help=f"Estimated {dm.B_HAT:.3f} (SE {dm.B_SE:.3f}) from national generation per person vs GDP per person, FY11–FY26 (growth on growth); levels cross-check {dm.B_LEVELS:.3f}")
k = st.sidebar.slider("Elasticity in 2047 as share of today's (maturing demand)", 0.50, 1.00, key="k", step=0.05)
pop = st.sidebar.slider("Population 2047, million", 1550, 1780, key="pop", step=5, help="UN WPP 2024 medium: 1,665 million")
ev = st.sidebar.select_slider("Electric-vehicle adoption", ["Slow", "Base", "Fast"], key="ev")
dc = st.sidebar.slider("Data centres in 2047, TWh", 80, 450, key="dc", step=10)
h2 = st.sidebar.slider("Green hydrogen in 2047, Mt a year", 0.0, 30.0, key="h2", step=0.5)
elec = st.sidebar.select_slider("Extra electrification: industrial heat + cooking", list(ELEC), key="elec",
                                help="Policy-driven switch of low-temperature industrial heat (<150 °C) and LPG cooking to electricity, "
                                     "beyond the historical trend. 2047 end-use TWh: Low 35 + 9, Base 139 + 37, High 314 + 94. "
                                     "Off in the headline forecast; see the Assumptions tab for the sizing.")
bridge = st.sidebar.slider("Generation needed per TWh of new load, 2047", 1.04, 1.18, key="bridge", step=0.01,
                           help="Delivery factor for EVs, data centres and electrification: transmission & distribution losses plus power-plant auxiliary use.")
st.sidebar.button("Reset to base case", on_click=reset)

P = dict(base, gdp=gdp / 100, b=(float(dm.B_HAT) if abs(b - round(float(dm.B_HAT), 3)) < 1e-9 else b), k=k, pop_2047=pop, ev_twh_2047=EV[ev], dc_twh_2047=dc,
         dc_twh_2040=dc * base["dc_twh_2040"] / base["dc_twh_2047"], h2_mt_2047=h2, bridge_2047=bridge,
         heat_twh_2047=ELEC[elec][0], cook_twh_2047=ELEC[elec][1])
DKEY = params_key(P); BKEY = params_key(base)
nb, stt, reg = run_demand(DKEY)
nb0, _, reg0 = run_demand(BKEY)
fy26 = hist.loc[2026, "generation_bu"]

# ------------------------------------------------------------------ header
tot = nb.loc[2047, "gen_total"]; mult = tot / fy26
o = run_mix(DKEY, 1200, 100, 0, 1.0, 3.0, 1.0, 1.0)
S = o["summary"]
hl, hr = st.columns([1, 1.35], gap="large")
with hl:
    st.markdown(f"""<div class="hero">
<h1>India will need {fmt0(tot)} TWh of electricity in 2047</h1>
<p class="lede">That is {mult:.1f} times what the country generated in FY26. Under a 1.2 Gt CO₂ cap, the least-cost plan makes
{S['non_fossil_%']:.0f}% of it without fossil fuels, with each grid region building on what its land, sun, wind and rivers offer.</p>
<div class="facts">
<div><b>{fmt0(mcq.loc['gen_total_2047','P10'])}–{fmt0(mcq.loc['gen_total_2047','P90'])}</b><span>TWh, likely range (P10–P90)</span></div>
<div><b>{S['non_fossil_%']:.0f}%</b><span>non-fossil generation</span></div>
<div><b>₹{S['cost_rs_per_kwh']:.2f}</b><span>average cost per kWh</span></div>
</div></div>""", unsafe_allow_html=True)
    st.caption(f"Base case {fmt0(nb0.loc[2047,'gen_total'])} TWh; {((mult ** (1/21)) - 1) * 100:.1f}% a year from FY26's {fmt0(fy26)} TWh. "
               "Forecast fitted on energy generated only. Move the sidebar sliders and everything re-runs.")
with hr:
    if o.get("status") == "Optimal":
        viz.grid_map_3d(o["gen"], o["demand"], o["flows"], SRC, LAB, height=500, key="hero_map")
        st.markdown(viz.legend([(r, REGCOL[r]) for r in REG]) +
                    '<p style="color:#93A3BA;font-size:0.88rem;margin-top:4px">Height = electricity generated in 2047. Arcs = net power sent between regions. Drag to tilt, hover for the mix.</p>',
                    unsafe_allow_html=True)

tabs = st.tabs(["Overview", "Demand forecast", "Generation mix", "Pathway to 2047", "Compare scenarios", "Validation", "Assumptions & sources"])


# ------------------------------------------------------------------ helpers
def stacked_regions(G, title_unit="TWh"):
    fig = go.Figure()
    for s in SRC:
        fig.add_bar(y=REG, x=[G.loc[r, s] for r in REG], name=LAB[s], orientation="h", marker_color=COL[s],
                    hovertemplate="%{y}: %{x:,.0f} " + title_unit + f" {LAB[s]}<extra></extra>")
    fig.update_layout(barmode="stack", height=320, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2),
                      xaxis_title=title_unit, yaxis=dict(autorange="reversed"))
    return fig


def fan_chart(series):
    fig = go.Figure()
    q = mc
    yrs = [2026, 2031, 2036, 2041, 2047]
    lo = [nb0.loc[2026, "gen_total"]] + [q[f"gen_total_{y}"].quantile(0.1) for y in yrs[1:]]
    hi = [nb0.loc[2026, "gen_total"]] + [q[f"gen_total_{y}"].quantile(0.9) for y in yrs[1:]]
    fig.add_scatter(x=yrs + yrs[::-1], y=hi + lo[::-1], fill="toself", fillcolor="rgba(58,134,200,0.15)", line=dict(width=0), mode="lines",
                    name="Monte Carlo P10–P90", hoverinfo="skip")
    fig.add_scatter(x=hist.index, y=hist.generation_bu, name="Actual (CEA)", line=dict(color="#E8EEF7", width=2.5))
    for name, s, style in series:
        fig.add_scatter(x=s.index, y=s.values, name=name, line=style)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2),
                      hovermode="x unified")
    return fig


# ================================================================== OVERVIEW
with tabs[0]:
    c = st.columns(3) + st.columns(3)
    c[0].metric("Generation FY2046-47", f"{fmt0(tot)} TWh", f"{tot - nb0.loc[2047,'gen_total']:+,.0f} vs base" if abs(tot - nb0.loc[2047, 'gen_total']) > 0.5 else None)
    c[1].metric("Grid demand (excl. H₂)", f"{fmt0(nb.loc[2047,'gen_grid'])} TWh")
    c[2].metric("Green-hydrogen electricity", f"{fmt0(nb.loc[2047,'gen_h2'])} TWh")
    nf26 = 100 - (fy26_reg.coal_lignite.sum() + fy26_reg.gas.sum()) / fy26_reg[['coal_lignite','gas','nuclear','hydro','solar','wind']].sum().sum() * 100
    c[3].metric("Non-fossil share 2047", f"{S['non_fossil_%']:.1f}%", help=f"FY26 actual: {nf26:.1f}%")
    c[4].metric("Power-sector CO₂ 2047", f"{fmt0(S['co2_mt'])} Mt")
    c[5].metric("Average system cost", f"₹{S['cost_rs_per_kwh']:.2f}/kWh")
    l, r = st.columns([1.15, 1])
    with l:
        st.subheader("Generation requirement: history and forecast")
        st.plotly_chart(fan_chart([("Current assumptions (total)", nb.gen_total, dict(color="#F5B83D", width=3)),
                                   ("Current assumptions (grid only)", nb.gen_grid, dict(color="#F5B83D", dash="dot")),
                                   ("Base case (total)", nb0.gen_total, dict(color="#4F9BF5", dash="dash"))]), width="stretch", key="c1")
    with r:
        st.subheader("Regional generation mix, FY2046-47")
        st.caption("Least-cost plan with CO₂ held at today's 1.2 Gt, for the current demand assumptions.")
        st.plotly_chart(stacked_regions(o["gen"]), width="stretch", key="c2")
    l, r = st.columns([1, 1.15])
    with l:
        st.subheader("Grid regions (CEA)")
        st.caption("States and union territories coloured by the CEA grid region they belong to.")
        st.plotly_chart(viz.region_choropleth(states), width="stretch", key="c3")
        st.markdown(viz.legend([(r, REGCOL[r]) for r in REG]), unsafe_allow_html=True)
    with r:
        st.subheader("Each region's role in 2047")
        G = o["gen"]; net = G.sum(axis=1) - o["demand"]
        tbl = pd.DataFrame({"Generation TWh": G.sum(axis=1), "Requirement TWh": o["demand"], "Net export TWh": net,
                            **{f"{LAB[s]} %": G[s] / G.sum(axis=1) * 100 for s in SRC}}).reindex(REG)
        st.dataframe(tbl.style.format("{:,.0f}", subset=["Generation TWh", "Requirement TWh", "Net export TWh"]).format("{:.1f}", subset=[f"{LAB[s]} %" for s in SRC]),
                     width="stretch", key="c4")
        st.markdown("- **Northern:** Rajasthan solar hub plus Himalayan hydro; exports midday solar.\n"
                    "- **Western:** coastal wind, large solar and the cheapest pithead coal (Chhattisgarh, Madhya Pradesh).\n"
                    "- **Southern:** wind in Tamil Nadu, Karnataka and Andhra Pradesh; nuclear firms the weaker sun.\n"
                    "- **Eastern:** weakest solar and no 150 m wind; pithead coal plus new nuclear, importing clean power.\n"
                    "- **North-Eastern:** Arunachal hydro, exported to the North and East.")

# ================================================================== DEMAND
with tabs[1]:
    st.caption("Use the sidebar to change the drivers. Results update instantly; the base case is shown dashed.")
    c = st.columns(5)
    c[0].metric("Total 2047", f"{fmt0(tot)} TWh", f"{tot - nb0.loc[2047,'gen_total']:+,.0f} vs base")
    c[1].metric("Organic demand (generation)", f"{fmt0(nb.loc[2047,'gen_organic'])} TWh")
    c[2].metric("EVs + data centres", f"{fmt0(nb.loc[2047,'gen_ev_dc'])} TWh")
    c[3].metric("Green hydrogen", f"{fmt0(nb.loc[2047,'gen_h2'])} TWh", f"{h2:.1f} Mt × {base['kwh_per_kg']:.0f} kWh/kg", delta_color="off")
    c[4].metric("Heat + cooking electrification", f"{fmt0(nb.loc[2047,'gen_elec'])} TWh", elec, delta_color="off")
    l, r = st.columns(2)
    with l:
        st.subheader("Selected vs base")
        st.plotly_chart(fan_chart([("Selected", nb.gen_total, dict(color="#F5B83D", width=3)), ("Base", nb0.gen_total, dict(color="#4F9BF5", dash="dash"))]),
                        width="stretch", key="c5")
    with r:
        st.subheader("What the demand is made of")
        fig = go.Figure()
        for col, name, cl in [("gen_organic", "Organic demand", "#4F9BF5"), ("gen_ev_dc", "EVs + data centres", "#F5B83D"), ("gen_elec", "Heat + cooking", "#E07A5F"), ("gen_h2", "Green hydrogen", "#3CC5A8")]:
            fig.add_scatter(x=nb.index, y=nb[col], stackgroup="one", name=name, line=dict(color=cl))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, width="stretch", key="c6")
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("Where the requirement comes from (FY24–FY26)")
        rh = csv("v2_regional_requirement_history.csv")
        rh = rh[rh.fy_end_year == 2026].set_index("cea_region").reindex(REG) / 1e3
        fig = go.Figure()
        fig.add_bar(x=REG, y=rh.generation, name="Generated in region", marker_color="#4F9BF5")
        fig.add_bar(x=REG, y=rh.requirement, name="Requirement (generation + net imports)", marker_color="#F5B83D")
        fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh, FY2025-26", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch", key="c7")
        st.caption("A region's production requirement is what was generated in it plus what it imported from other regions "
                   "(Grid-India inter-regional exchange). Generation data only: NPP/CEA monthly reports.")
    with r:
        st.subheader("By region")
        rr = reg[reg.fy_end.isin([2030, 2035, 2040, 2047])].pivot(index="region", columns="fy_end", values="gen_total_twh").reindex(REG)
        fig = go.Figure()
        for y, cl in zip(rr.columns, ["#5A6B84", "#A88BFA", "#4F9BF5", "#F5B83D"]):
            fig.add_bar(x=REG, y=rr[y], name=f"FY{str(y)[2:]}", marker_color=cl)
        fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch", key="c8")
    st.subheader("Trace the forecast for one region")
    sc = st.selectbox("CEA region", REG, index=2)
    t = stt[stt.region == sc].set_index("fy_end")[["pop_k", "urban", "gsdp_index", "kwh_gen_pc", "organic_twh"]]
    t["gsdp_index"] = t.gsdp_index / t.gsdp_index.iloc[0] * 100
    t.columns = ["Population (thousand)", "Urban %", "Real GSDP (FY26 = 100)", "kWh generated per person", "Requirement before new loads, TWh"]
    st.caption(f"Each year: kWh generated per person grows with the region's real GSDP per person at elasticity b = {b:.3f} "
               f"(fading to {k:.2f}·b by 2047); requirement = population × kWh per person. FY26 starts from the region's share "
               "of national generation (own generation + net imports, FY24–26 average). New loads are added on top.")
    st.dataframe(t.loc[[2026, 2030, 2035, 2040, 2047]].style.format("{:,.1f}"), width="stretch", key="c9")
    st.download_button("Download all regions × years (CSV)", stt.to_csv(index=False).encode(), "regional_demand_forecast.csv")

# ================================================================== MIX
with tabs[2]:
    st.caption("Each change solves the least-cost optimiser again for FY2046-47 (5 regions × 6 sources × 12 time slices), using the demand from the sidebar.")
    c = st.columns(3)
    co2 = c[0].slider("CO₂ cap, Mt", 600, 2000, 1200, 50, help="Today ≈ 1,200 Mt. Draft-NEP-like ≈ 1,700 Mt.")
    nuc = c[1].selectbox("Nuclear policy", ["Least cost (≤ 100 GW)", "Mission (100 GW)", "Delayed (≤ 50 GW)"])
    rem = c[2].slider("Solar & wind build speed", 0.6, 1.4, 1.0, 0.05, help=f"1.0 = {M.A.solar_cap_2047_gw:,.0f} GW solar and {M.A.wind_cap_2047_gw:,.0f} GW wind by 2047")
    c = st.columns(3)
    tx = c[0].slider("Inter-regional transmission × today", 1.0, 5.0, 3.0, 0.5)
    sto = c[1].slider("Storage cost × 2026", 0.5, 2.0, 1.0, 0.1)
    sol = c[2].slider("Solar cost × 2026", 0.6, 1.6, 1.0, 0.1)
    nuc_cap, nuc_floor = {"Least cost (≤ 100 GW)": (100, 0), "Mission (100 GW)": (100, 100), "Delayed (≤ 50 GW)": (50, 0)}[nuc]
    with st.spinner("Solving…"):
        o = run_mix(DKEY, co2, nuc_cap, nuc_floor, rem, tx, sto, sol)
    if o.get("status") != "Optimal":
        st.error(f"No solution: {o.get('status')}")
    else:
        S = o["summary"]; G, C = o["gen"], o["cap"]
        if o["unserved"] > 0.5:
            st.warning(f"Not deliverable within the build limits: {o['unserved']:,.0f} TWh of demand cannot be served. Build faster or reduce demand.")
        if o["co2_excess"] > 0.5:
            st.warning(f"The CO₂ cap cannot be met: emissions exceed it by {o['co2_excess']:,.0f} Mt.")
        c = st.columns(6)
        c[0].metric("Non-fossil share", f"{S['non_fossil_%']:.1f}%")
        c[1].metric("CO₂", f"{fmt0(S['co2_mt'])} Mt")
        c[2].metric("System cost", f"₹{S['cost_rs_per_kwh']:.2f}/kWh")
        c[3].metric("Carbon price (marginal)", f"₹{fmt0(S['co2_shadow_rs_per_t'])}/t")
        c[4].metric("Batteries", f"{fmt0(o['bess'].sum())} GW")
        c[5].metric("Pumped storage", f"{fmt0(o['psp'].sum())} GW")
        l, r = st.columns([1, 1.3])
        with l:
            st.subheader("National mix")
            nat = G.sum()
            fig = go.Figure(go.Pie(labels=[LAB[s] for s in SRC], values=[nat[s] for s in SRC], hole=0.55, marker_colors=[COL[s] for s in SRC],
                                   sort=False, texttemplate="%{label}<br>%{percent:.1%}", hovertemplate="%{label}: %{value:,.0f} TWh<extra></extra>"))
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, width="stretch", key="c10")
        with r:
            st.subheader("Regional mix (TWh)")
            st.plotly_chart(stacked_regions(G), width="stretch", key="c11")
        st.subheader("This scenario on the map")
        viz.grid_map_3d(G, o["demand"], o["flows"], SRC, LAB, height=460, key="mix_map")
        st.caption("Height = electricity generated in 2047 under the settings above. Arcs = net power traded between regions. Hover a region for its mix.")
        l, r = st.columns(2)
        with l:
            st.subheader("Who exports, who imports")
            net = (G.sum(axis=1) - o["demand"]).reindex(REG)
            fig = go.Figure(go.Bar(x=net.values, y=REG, orientation="h", marker_color=["#3CC5A8" if v > 0 else "#E07A5F" for v in net.values],
                                   hovertemplate="%{y}: %{x:+,.0f} TWh<extra></extra>"))
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Net export, TWh", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, width="stretch", key="c12")
        with r:
            st.subheader("How each season and time of day is supplied")
            gs = o["gen_slices"].groupby(["season", "period", "source"]).twh.sum().unstack()
            order = [(s, p) for s in M.SEAS for p in M.PER]
            gs = gs.reindex(order); hrs = np.array([M.HRS[t] for t in order])
            sto_d = o["storage"].groupby(["season", "period"]).discharge_twh.sum().reindex(order).values
            fig = go.Figure(); xl = [f"{s[:3]} {p[:3]}" for s, p in order]
            for s in SRC:
                fig.add_bar(x=xl, y=gs[s].values / hrs * 1000, name=LAB[s], marker_color=COL[s])
            fig.add_bar(x=xl, y=sto_d / hrs * 1000, name="Storage discharge", marker_color=COL["bess"])
            fig.update_layout(barmode="stack", height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Average GW", legend=dict(orientation="h", y=-0.35))
            st.plotly_chart(fig, width="stretch", key="c13")
        st.subheader("Capacity needed (GW)")
        capt = C.assign(Batteries=o["bess"], **{"Pumped storage": o["psp"]}).rename(columns=LAB).reindex(REG)
        capt.loc["India"] = capt.sum()
        st.dataframe(capt.style.format("{:,.1f}"), width="stretch", key="c14")
        with st.expander(f"Independent checks on this solution: {int(o['checks']['pass'].sum())}/{len(o['checks'])} pass"):
            st.dataframe(o["checks"].astype(str), width="stretch", hide_index=True)
        if st.button("Save this setting for comparison"):
            st.session_state.setdefault("saved", []).append({
                "Scenario": f"GDP {gdp}%, b {b}, H₂ {h2} Mt, elec {elec} | CO₂ {co2}, {nuc.split(' (')[0]}, build ×{rem}, tx ×{tx}",
                "Requirement TWh": tot, **{f"{LAB[s]} %": G[s].sum() / G.sum().sum() * 100 for s in SRC},
                "Non-fossil %": S["non_fossil_%"], "CO₂ Mt": S["co2_mt"], "₹/kWh": S["cost_rs_per_kwh"],
                "Unserved TWh": o["unserved"], "Over cap Mt": o["co2_excess"]})
            st.success("Saved. See the Compare scenarios tab.")

# ================================================================== PATHWAY
with tabs[3]:
    st.caption("The optimiser solved at FY30, FY35, FY40 and FY47 with each year's demand (from the sidebar), committed fleet, "
               "build limits anchored to CEA's 2035-36 projection, transmission growth and a CO₂ path of 1.40 / 1.45 / 1.35 / 1.20 Gt.")
    with st.spinner("Solving four milestone years…"):
        pw = run_pathway(DKEY)
    act = fy26_reg[["coal_lignite", "gas", "nuclear", "hydro", "solar", "wind"]].sum(); act.index = SRC
    yrs = ["FY26 (actual)"] + [f"FY{str(y)[2:]}" for y in pw.index]
    l, r = st.columns(2)
    with l:
        st.subheader("Generation by source (TWh)")
        fig = go.Figure()
        for s in SRC:
            fig.add_bar(x=yrs, y=[act[s]] + list(pw[s]), name=LAB[s], marker_color=COL[s])
        fig.update_layout(barmode="stack", height=380, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch", key="c15")
    with r:
        st.subheader("Installed capacity (GW)")
        fig = go.Figure()
        now = dict(coal=228.5, nuclear=8.78, hydro=51.4, solar=150.3, wind=56.1)
        for s in ["coal", "nuclear", "hydro", "solar", "wind"]:
            fig.add_scatter(x=[2026] + list(pw.index), y=[now[s]] + list(pw[f"{s}_gw"]), name=LAB[s], line=dict(color=COL[s], width=2.5))
        fig.add_scatter(x=list(pw.index), y=pw.bess_gw, name="Batteries", line=dict(color=COL["bess"], width=2.5))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, width="stretch", key="c16")
    tbl = pd.DataFrame({"Total TWh": [act.sum()] + list(pw[SRC].sum(axis=1)),
                        "Coal %": [act.coal / act.sum() * 100] + list(pw.coal / pw[SRC].sum(axis=1) * 100),
                        "Non-fossil %": [(1 - (act.coal + act.gas) / act.sum()) * 100] + list((1 - (pw.coal + pw.gas) / pw[SRC].sum(axis=1)) * 100),
                        "CO₂ Mt": [0.96 * act.coal + 0.40 * act.gas] + list(pw.co2_mt),
                        "CO₂ cap Mt": [np.nan] + list(pw.co2_cap), "Unserved TWh": [np.nan] + list(pw.unserved)}, index=yrs).astype(float)
    st.dataframe(tbl.style.format("{:,.1f}", na_rep="—"), width="stretch", key="c17")
    st.subheader("Regional mix by year")
    yy = st.select_slider("Year", list(pw.index), value=2047)
    Gy = pd.DataFrame({s: {r: pw.loc[yy, f"{r}|{s}"] for r in REG} for s in SRC})
    st.plotly_chart(stacked_regions(Gy), width="stretch", key="c18")

# ================================================================== COMPARE
with tabs[4]:
    st.markdown("Save settings from the **Generation mix** tab to compare them here. Two reference cases are always shown.")
    refs = []
    for name, kw in [("Base: CO₂ 1.2 Gt", (1200, 100, 0)), ("Draft-NEP-like: CO₂ 1.7 Gt", (1700, 100, 0))]:
        oo = run_mix(BKEY, kw[0], kw[1], kw[2], 1.0, 3.0, 1.0, 1.0); G = oo["gen"]; Sx = oo["summary"]
        refs.append({"Scenario": name, "Requirement TWh": nb0.loc[2047, "gen_total"], **{f"{LAB[s]} %": G[s].sum() / G.sum().sum() * 100 for s in SRC},
                     "Non-fossil %": Sx["non_fossil_%"], "CO₂ Mt": Sx["co2_mt"], "₹/kWh": Sx["cost_rs_per_kwh"], "Unserved TWh": oo["unserved"], "Over cap Mt": oo["co2_excess"]})
    comp = pd.DataFrame(refs + st.session_state.get("saved", [])).set_index("Scenario")
    st.dataframe(comp.style.format("{:,.1f}"), width="stretch", key="c19")
    fig = go.Figure()
    for s in SRC:
        fig.add_bar(y=comp.index, x=comp[f"{LAB[s]} %"], name=LAB[s], orientation="h", marker_color=COL[s])
    fig.update_layout(barmode="stack", height=120 + 50 * len(comp), margin=dict(l=10, r=10, t=10, b=10), xaxis_title="% of generation",
                      legend=dict(orientation="h", y=-0.3), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch", key="c20")
    if st.session_state.get("saved") and st.button("Clear saved scenarios"):
        st.session_state["saved"] = []; st.rerun()
    st.subheader("What moves the 2047 demand most (one driver at a time)")
    tor = csv("v2_tornado.csv").sort_values("span")
    fig = go.Figure()
    fig.add_bar(y=tor.driver, x=tor.low, orientation="h", name="Low value", marker_color="#5A6B84")
    fig.add_bar(y=tor.driver, x=tor.high, orientation="h", name="High value", marker_color="#3CC5A8")
    fig.update_layout(barmode="overlay", height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Change vs base, TWh", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch", key="c21")

# ================================================================== VALIDATION
with tabs[5]:
    l, r = st.columns(2)
    with l:
        st.subheader("Backcast: the optimiser on FY26's fleet and demand")
        bk = csv("backcast_fy26.csv"); n_ = bk[bk.region == "India"].set_index("source")
        fig = go.Figure()
        fig.add_bar(x=[LAB[s] for s in SRC], y=n_.loc[SRC, "actual_twh"], name="Actual (CEA)", marker_color="#5A6B84")
        fig.add_bar(x=[LAB[s] for s in SRC], y=n_.loc[SRC, "model_twh"], name="Model", marker_color="#4F9BF5")
        fig.update_layout(barmode="group", height=330, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch", key="c22")
        st.caption("Regional coal is placed within 6% of national coal. Gas runs on contracts in reality, which a least-cost model does not see.")
        st.dataframe(bk[bk.source == "coal"].drop(columns="source").set_index("region"), width="stretch", key="c23")
    with r:
        st.subheader("Against official and published numbers")
        st.dataframe(pd.read_csv(OUT / "dash" / "benchmarks.csv"), width="stretch", hide_index=True)
        st.subheader("Model coefficients (generation basis)")
        st.dataframe(csv("v2_coefficients.csv"), width="stretch", hide_index=True)
        st.caption("Back-test on generation: elasticity fitted to FY11–FY19 only predicts FY24 and FY25 within about 1% (FY26, a cool wet year, +6%); a naive trend misses by 5–10%.")
    st.subheader("Demand model tests")
    st.dataframe(csv("v2_tests.csv"), width="stretch", hide_index=True)

# ================================================================== ASSUMPTIONS
with tabs[6]:
    a = pd.read_csv(OUT / "dash" / "assumptions.csv")
    q = st.text_input("Search assumptions")
    st.dataframe(a[a.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)] if q else a, width="stretch", hide_index=True)
    l, r = st.columns(2)
    with l:
        st.subheader("Resource potential vs base 2047 use (GW)")
        st.dataframe(pd.read_csv(OUT / "dash" / "resources_vs_use.csv").set_index("region"), width="stretch", key="c24")
    with r:
        st.subheader("Data sources")
        st.dataframe(pd.read_csv(OUT / "dash" / "sources.csv"), width="stretch", hide_index=True)
    st.info("AI tools: built with help from Claude (Anthropic) for data gathering, coding and drafting, as the competition terms require us to disclose. "
            "All numbers come from the cited sources and the team's own reproducible model runs.")
