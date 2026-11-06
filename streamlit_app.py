"""India 2047 Electricity Generation Forecast — interactive dashboard (ExxonMobil INNOTHON 2026).

Run locally:  streamlit run streamlit_app.py
Every number is computed live by the project's own models:
  model/demand_v1.py  state panel demand model      model/regional.py  roll-up to CEA regions
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

st.set_page_config(page_title="India 2047 Electricity Forecast", page_icon="⚡", layout="wide")

SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
LAB = dict(coal="Coal", gas="Natural gas", nuclear="Nuclear", hydro="Hydro", solar="Solar", wind="Wind", bess="Batteries", psp="Pumped storage")
COL = dict(coal="#6E6E73", gas="#B07D3A", nuclear="#8A6CC9", hydro="#3A86C8", solar="#E0AA22", wind="#34A585", bess="#D0587E", psp="#5B8DB8")
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
REGCOL = {"Northern": "#E0AA22", "Western": "#C9821B", "Southern": "#34A585", "Eastern": "#6E6E73", "North-Eastern": "#3A86C8"}
OUT = ROOT / "out"; DATA = ROOT / "data"
fmt0 = lambda v: f"{v:,.0f}"


# ------------------------------------------------------------------ models (cached)
@st.cache_resource(show_spinner="Loading models and fitting the state panel…")
def models():
    import demand_v1 as dm
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
mcq = csv("v1_mc_quantiles_2047.csv").set_index("Unnamed: 0")
mc = csv("v1_montecarlo.csv")

# ------------------------------------------------------------------ sidebar: demand assumptions
st.sidebar.title("Demand assumptions")
st.sidebar.caption("Every change re-runs the state demand model, the regional split, the optimiser and the pathway.")
base = dm.SCEN["Base"]
EV = {"Slow": dm.ev_2047("low"), "Base": dm.ev_2047("base"), "Fast": dm.ev_2047("high")}


def reset():
    for k, v in dict(gdp=6.5, b=round(float(dm.B_HAT), 3), k=0.75, pop=1665, ev="Base", dc=250, h2=12.0, bridge=1.06).items():
        st.session_state[k] = v


if "gdp" not in st.session_state:
    reset()
gdp = st.sidebar.slider("Real GDP growth, % a year", 4.5, 8.5, key="gdp", step=0.1)
b = st.sidebar.slider("Income elasticity of electricity use", 0.50, 1.00, key="b", step=0.01,
                      help=f"Estimated {dm.B_HAT:.3f} (SE {dm.B_SE:.3f}) from a 32-state fixed-effects panel")
k = st.sidebar.slider("Elasticity in 2047 as share of today's (maturing demand)", 0.50, 1.00, key="k", step=0.05)
pop = st.sidebar.slider("Population 2047, million", 1550, 1780, key="pop", step=5, help="UN WPP 2024 medium: 1,665 million")
ev = st.sidebar.select_slider("Electric-vehicle adoption", ["Slow", "Base", "Fast"], key="ev")
dc = st.sidebar.slider("Data centres in 2047, TWh", 80, 450, key="dc", step=10)
h2 = st.sidebar.slider("Green hydrogen in 2047, Mt a year", 0.0, 30.0, key="h2", step=0.5)
bridge = st.sidebar.slider("Generation ÷ consumption ratio in 2047", 1.03, 1.09, key="bridge", step=0.005)
st.sidebar.button("Reset to base case", on_click=reset)

P = dict(base, gdp=gdp / 100, b=(float(dm.B_HAT) if abs(b - round(float(dm.B_HAT), 3)) < 1e-9 else b), k=k, pop_2047=pop, ev_twh_2047=EV[ev], dc_twh_2047=dc,
         dc_twh_2040=dc * base["dc_twh_2040"] / base["dc_twh_2047"], h2_mt_2047=h2, bridge_2047=bridge)
DKEY = params_key(P); BKEY = params_key(base)
nb, stt, reg = run_demand(DKEY)
nb0, _, reg0 = run_demand(BKEY)
fy26 = hist.loc[2026, "generation_bu"]

# ------------------------------------------------------------------ header
st.title("India 2047 electricity generation forecast")
tot = nb.loc[2047, "gen_total"]; mult = tot / fy26
st.markdown(f"**{fmt0(tot)} TWh** of electricity generation in FY2046-47 under the current assumptions: **{mult:.1f}×** FY26 "
            f"({fmt0(fy26)} TWh), {((mult ** (1/21)) - 1) * 100:.1f}% a year. Base case {fmt0(nb0.loc[2047,'gen_total'])} TWh; "
            f"Monte Carlo P10–P90 {fmt0(mcq.loc['gen_total_2047','P10'])}–{fmt0(mcq.loc['gen_total_2047','P90'])} TWh.")

tabs = st.tabs(["Overview", "Demand forecast", "Generation mix", "Pathway to 2047", "Compare scenarios", "Validation", "Assumptions & sources"])


# ------------------------------------------------------------------ helpers
def tile_map(values, title, fmt=lambda v: fmt0(v), colorscale=None, by_region=False):
    """Schematic tile map of states (not a geographic boundary map)."""
    TILE = dict(JK=(2, 0), LA=(3, 0), CH=(0, 1), PB=(1, 1), HP=(2, 1), UK=(3, 1), SK=(5, 1), AR=(7, 1),
                RJ=(0, 2), HR=(1, 2), DL=(2, 2), UP=(3, 2), BR=(4, 2), AS=(6, 2), NL=(7, 2),
                GJ=(0, 3), MP=(1, 3), CG=(2, 3), JH=(3, 3), WB=(4, 3), ML=(6, 3), MN=(7, 3),
                DN=(0, 4), MH=(1, 4), TG=(2, 4), OD=(3, 4), TR=(6, 4), MZ=(7, 4),
                GA=(0, 5), KA=(1, 5), AP=(2, 5), LD=(0, 6), KL=(1, 6), TN=(2, 6), PY=(3, 6), AN=(5, 6))
    s = states.set_index("code")
    fig = go.Figure()
    for code, (x, y) in TILE.items():
        r = s.loc[code, "cea_region"]; v = values.get(code, np.nan) if not by_region else None
        fill = REGCOL[r] if by_region else None
        fig.add_shape(type="rect", x0=x, x1=x + 0.94, y0=-y, y1=-y - 0.94, line=dict(color="white", width=1),
                      fillcolor=fill if by_region else "rgba(0,0,0,0)")
    xs, ys, txt, vals, hov = [], [], [], [], []
    for code, (x, y) in TILE.items():
        xs.append(x + 0.47); ys.append(-y - 0.47); txt.append(code)
        v = values.get(code, np.nan); vals.append(v)
        hov.append(f"{s.loc[code,'state']} ({s.loc[code,'cea_region']})" + ("" if by_region or pd.isna(v) else f"<br>{title}: {fmt(v)}"))
    if by_region:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="text", text=txt, hovertext=hov, hoverinfo="text", textfont=dict(color="white", size=13)))
    else:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=txt, hovertext=hov, hoverinfo="text",
                                 marker=dict(symbol="square", size=44, color=vals, colorscale=colorscale or "YlOrBr", showscale=True,
                                             colorbar=dict(title=title, thickness=12), line=dict(color="white", width=1)),
                                 textfont=dict(color="black", size=12)))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False, range=[-0.3, 8.2]), yaxis=dict(visible=False, range=[-7.2, 0.3], scaleanchor="x"))
    return fig


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
    fig.add_scatter(x=yrs + yrs[::-1], y=hi + lo[::-1], fill="toself", fillcolor="rgba(58,134,200,0.15)", line=dict(width=0),
                    name="Monte Carlo P10–P90", hoverinfo="skip")
    fig.add_scatter(x=hist.index, y=hist.generation_bu, name="Actual (CEA)", line=dict(color="#1B2433", width=2.5))
    for name, s, style in series:
        fig.add_scatter(x=s.index, y=s.values, name=name, line=style)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2),
                      hovermode="x unified")
    return fig


# ================================================================== OVERVIEW
with tabs[0]:
    o = run_mix(DKEY, 1200, 100, 0, 1.0, 3.0, 1.0, 1.0)
    S = o["summary"]
    c = st.columns(6)
    c[0].metric("Generation FY2046-47", f"{fmt0(tot)} TWh", f"{tot - nb0.loc[2047,'gen_total']:+,.0f} vs base" if abs(tot - nb0.loc[2047, 'gen_total']) > 0.5 else None)
    c[1].metric("Grid demand (excl. H₂)", f"{fmt0(nb.loc[2047,'gen_grid'])} TWh")
    c[2].metric("Green-hydrogen electricity", f"{fmt0(nb.loc[2047,'gen_h2'])} TWh")
    c[3].metric("Non-fossil share 2047", f"{S['non_fossil_%']:.1f}%", f"FY26: {100 - (fy26_reg.coal_lignite.sum() + fy26_reg.gas.sum()) / fy26_reg[['coal_lignite','gas','nuclear','hydro','solar','wind']].sum().sum() * 100:.1f}%", delta_color="off")
    c[4].metric("Power-sector CO₂ 2047", f"{fmt0(S['co2_mt'])} Mt")
    c[5].metric("Average system cost", f"₹{S['cost_rs_per_kwh']:.2f}/kWh")
    l, r = st.columns([1.15, 1])
    with l:
        st.subheader("Generation requirement: history and forecast")
        st.plotly_chart(fan_chart([("Current assumptions (total)", nb.gen_total, dict(color="#D0587E", width=3)),
                                   ("Current assumptions (grid only)", nb.gen_grid, dict(color="#D0587E", dash="dot")),
                                   ("Base case (total)", nb0.gen_total, dict(color="#3A86C8", dash="dash"))]), use_container_width=True, key="c1")
    with r:
        st.subheader("Regional generation mix, FY2046-47")
        st.caption("Least-cost plan with CO₂ held at today's 1.2 Gt, for the current demand assumptions.")
        st.plotly_chart(stacked_regions(o["gen"]), use_container_width=True, key="c2")
    l, r = st.columns([1, 1.15])
    with l:
        st.subheader("Grid regions (CEA)")
        st.caption("Schematic tile map: one square per state or union territory, coloured by CEA grid region. Not a boundary map.")
        st.plotly_chart(tile_map({}, "", by_region=True), use_container_width=True, key="c3")
    with r:
        st.subheader("Each region's role in 2047")
        G = o["gen"]; net = G.sum(axis=1) - o["demand"]
        tbl = pd.DataFrame({"Generation TWh": G.sum(axis=1), "Demand TWh": o["demand"], "Net export TWh": net,
                            **{f"{LAB[s]} %": G[s] / G.sum(axis=1) * 100 for s in SRC}}).reindex(REG)
        st.dataframe(tbl.style.format("{:,.0f}", subset=["Generation TWh", "Demand TWh", "Net export TWh"]).format("{:.1f}", subset=[f"{LAB[s]} %" for s in SRC]),
                     use_container_width=True, key="c4")
        st.markdown("- **Northern:** Rajasthan solar hub plus Himalayan hydro; exports midday solar.\n"
                    "- **Western:** coastal wind, large solar and the cheapest pithead coal (Chhattisgarh, Madhya Pradesh).\n"
                    "- **Southern:** wind in Tamil Nadu, Karnataka and Andhra Pradesh; nuclear firms the weaker sun.\n"
                    "- **Eastern:** weakest solar and no 150 m wind; pithead coal plus new nuclear, importing clean power.\n"
                    "- **North-Eastern:** Arunachal hydro, exported to the North and East.")

# ================================================================== DEMAND
with tabs[1]:
    st.caption("Use the sidebar to change the drivers. Results update instantly; the base case is shown dashed.")
    c = st.columns(4)
    c[0].metric("Total 2047", f"{fmt0(tot)} TWh", f"{tot - nb0.loc[2047,'gen_total']:+,.0f} vs base")
    c[1].metric("Organic demand (generation)", f"{fmt0(nb.loc[2047,'gen_organic'])} TWh")
    c[2].metric("EVs + data centres", f"{fmt0(nb.loc[2047,'gen_ev_dc'])} TWh")
    c[3].metric("Green hydrogen", f"{fmt0(nb.loc[2047,'gen_h2'])} TWh", f"{h2:.1f} Mt × {base['kwh_per_kg']:.0f} kWh/kg", delta_color="off")
    l, r = st.columns(2)
    with l:
        st.subheader("Selected vs base")
        st.plotly_chart(fan_chart([("Selected", nb.gen_total, dict(color="#D0587E", width=3)), ("Base", nb0.gen_total, dict(color="#3A86C8", dash="dash"))]),
                        use_container_width=True, key="c5")
    with r:
        st.subheader("What the demand is made of")
        fig = go.Figure()
        for col, name, cl in [("gen_organic", "Organic demand", "#3A86C8"), ("gen_ev_dc", "EVs + data centres", "#D0587E"), ("gen_h2", "Green hydrogen", "#34A585")]:
            fig.add_scatter(x=nb.index, y=nb[col], stackgroup="one", name=name, line=dict(color=cl))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True, key="c6")
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("Demand growth by state, FY26 → FY47")
        s26 = stt[stt.fy_end == 2026].set_index("code").req_twh; s47 = stt[stt.fy_end == 2047].set_index("code").req_twh
        metric = st.radio("Colour by", ["2047 requirement (TWh)", "Growth multiple"], horizontal=True, key="mapm")
        vals = (s47 if metric.startswith("2047") else (s47 / s26)).to_dict()
        st.plotly_chart(tile_map(vals, "TWh" if metric.startswith("2047") else "× FY26", fmt=(fmt0 if metric.startswith("2047") else (lambda v: f"{v:.2f}×"))),
                        use_container_width=True, key="c7")
    with r:
        st.subheader("By region")
        rr = reg[reg.fy_end.isin([2030, 2035, 2040, 2047])].pivot(index="region", columns="fy_end", values="gen_total_twh").reindex(REG)
        fig = go.Figure()
        for y, cl in zip(rr.columns, ["#C8CDD6", "#B07D3A", "#3A86C8", "#D0587E"]):
            fig.add_bar(x=REG, y=rr[y], name=f"FY{str(y)[2:]}", marker_color=cl)
        fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh generated", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True, key="c8")
    st.subheader("Trace the forecast for one state")
    names = states.set_index("code").state
    codes = [c for c in stt.code.unique() if c in names.index]
    sc = st.selectbox("State or union territory", codes, format_func=lambda c: f"{names[c]} ({c})", index=codes.index("KA") if "KA" in codes else 0)
    t = stt[stt.code == sc].set_index("fy_end")[["pop_k", "urban", "kwh_pc", "req_twh"]]
    t.columns = ["Population (thousand)", "Urban %", "kWh per person", "Requirement TWh"]
    st.caption(f"Each year: kWh per person grows with income per person at elasticity b × (fading to {k:.2f}·b by 2047), "
               f"adjusted for urbanisation (coefficient {dm.C_HAT:.4f}); requirement = population × kWh per person. "
               "New loads (EVs, data centres, hydrogen) are added at regional level.")
    st.dataframe(t.loc[[2026, 2030, 2035, 2040, 2047]].style.format("{:,.1f}"), use_container_width=True, key="c9")
    st.download_button("Download all states × years (CSV)", stt.to_csv(index=False).encode(), "state_demand_forecast.csv")

# ================================================================== MIX
with tabs[2]:
    st.caption("Each change solves the least-cost optimiser again for FY2046-47 (5 regions × 6 sources × 12 time slices), using the demand from the sidebar.")
    c = st.columns(6)
    co2 = c[0].slider("CO₂ cap, Mt", 600, 2000, 1200, 50, help="Today ≈ 1,200 Mt. Draft-NEP-like ≈ 1,700 Mt.")
    nuc = c[1].selectbox("Nuclear policy", ["Least cost, up to 100 GW", "Mission: exactly 100 GW", "Delayed: at most 50 GW"])
    rem = c[2].slider("Solar & wind build speed", 0.6, 1.4, 1.0, 0.05, help="1.0 = 1,279 GW solar and 375 GW wind by 2047")
    tx = c[3].slider("Inter-regional transmission × today", 1.0, 5.0, 3.0, 0.5)
    sto = c[4].slider("Storage cost × 2026", 0.5, 2.0, 1.0, 0.1)
    sol = c[5].slider("Solar cost × 2026", 0.6, 1.6, 1.0, 0.1)
    nuc_cap, nuc_floor = {"Least cost, up to 100 GW": (100, 0), "Mission: exactly 100 GW": (100, 100), "Delayed: at most 50 GW": (50, 0)}[nuc]
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
            st.plotly_chart(fig, use_container_width=True, key="c10")
        with r:
            st.subheader("Regional mix (TWh)")
            st.plotly_chart(stacked_regions(G), use_container_width=True, key="c11")
        l, r = st.columns(2)
        with l:
            st.subheader("Who exports, who imports")
            net = (G.sum(axis=1) - o["demand"]).reindex(REG)
            fig = go.Figure(go.Bar(x=net.values, y=REG, orientation="h", marker_color=["#34A585" if v > 0 else "#C9821B" for v in net.values],
                                   hovertemplate="%{y}: %{x:+,.0f} TWh<extra></extra>"))
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Net export, TWh", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True, key="c12")
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
            st.plotly_chart(fig, use_container_width=True, key="c13")
        st.subheader("Capacity needed (GW)")
        capt = C.assign(Batteries=o["bess"], **{"Pumped storage": o["psp"]}).rename(columns=LAB).reindex(REG)
        capt.loc["India"] = capt.sum()
        st.dataframe(capt.style.format("{:,.1f}"), use_container_width=True, key="c14")
        with st.expander(f"Independent checks on this solution: {int(o['checks']['pass'].sum())}/{len(o['checks'])} pass"):
            st.dataframe(o["checks"].astype(str), use_container_width=True, hide_index=True)
        if st.button("Save this setting for comparison"):
            st.session_state.setdefault("saved", []).append({
                "Scenario": f"GDP {gdp}%, b {b}, H₂ {h2} Mt | CO₂ {co2}, {nuc.split(':')[0]}, build ×{rem}, tx ×{tx}",
                "Demand TWh": tot, **{f"{LAB[s]} %": G[s].sum() / G.sum().sum() * 100 for s in SRC},
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
        st.plotly_chart(fig, use_container_width=True, key="c15")
    with r:
        st.subheader("Installed capacity (GW)")
        fig = go.Figure()
        now = dict(coal=228.5, nuclear=8.78, hydro=51.4, solar=150.3, wind=56.1)
        for s in ["coal", "nuclear", "hydro", "solar", "wind"]:
            fig.add_scatter(x=[2026] + list(pw.index), y=[now[s]] + list(pw[f"{s}_gw"]), name=LAB[s], line=dict(color=COL[s], width=2.5))
        fig.add_scatter(x=list(pw.index), y=pw.bess_gw, name="Batteries", line=dict(color=COL["bess"], width=2.5))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True, key="c16")
    tbl = pd.DataFrame({"Total TWh": [act.sum()] + list(pw[SRC].sum(axis=1)),
                        "Coal %": [act.coal / act.sum() * 100] + list(pw.coal / pw[SRC].sum(axis=1) * 100),
                        "Non-fossil %": [(1 - (act.coal + act.gas) / act.sum()) * 100] + list((1 - (pw.coal + pw.gas) / pw[SRC].sum(axis=1)) * 100),
                        "CO₂ Mt": [0.96 * act.coal + 0.40 * act.gas] + list(pw.co2_mt),
                        "CO₂ cap Mt": [np.nan] + list(pw.co2_cap), "Unserved TWh": [np.nan] + list(pw.unserved)}, index=yrs)
    st.dataframe(tbl.style.format("{:,.1f}", na_rep="—"), use_container_width=True, key="c17")
    st.subheader("Regional mix by year")
    yy = st.select_slider("Year", list(pw.index), value=2047)
    Gy = pd.DataFrame({s: {r: pw.loc[yy, f"{r}|{s}"] for r in REG} for s in SRC})
    st.plotly_chart(stacked_regions(Gy), use_container_width=True, key="c18")

# ================================================================== COMPARE
with tabs[4]:
    st.markdown("Save settings from the **Generation mix** tab to compare them here. Two reference cases are always shown.")
    refs = []
    for name, kw in [("Base: CO₂ 1.2 Gt", (1200, 100, 0)), ("Draft-NEP-like: CO₂ 1.7 Gt", (1700, 100, 0))]:
        oo = run_mix(BKEY, kw[0], kw[1], kw[2], 1.0, 3.0, 1.0, 1.0); G = oo["gen"]; Sx = oo["summary"]
        refs.append({"Scenario": name, "Demand TWh": nb0.loc[2047, "gen_total"], **{f"{LAB[s]} %": G[s].sum() / G.sum().sum() * 100 for s in SRC},
                     "Non-fossil %": Sx["non_fossil_%"], "CO₂ Mt": Sx["co2_mt"], "₹/kWh": Sx["cost_rs_per_kwh"], "Unserved TWh": oo["unserved"], "Over cap Mt": oo["co2_excess"]})
    comp = pd.DataFrame(refs + st.session_state.get("saved", [])).set_index("Scenario")
    st.dataframe(comp.style.format("{:,.1f}"), use_container_width=True, key="c19")
    fig = go.Figure()
    for s in SRC:
        fig.add_bar(y=comp.index, x=comp[f"{LAB[s]} %"], name=LAB[s], orientation="h", marker_color=COL[s])
    fig.update_layout(barmode="stack", height=120 + 50 * len(comp), margin=dict(l=10, r=10, t=10, b=10), xaxis_title="% of generation",
                      legend=dict(orientation="h", y=-0.3), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True, key="c20")
    if st.session_state.get("saved") and st.button("Clear saved scenarios"):
        st.session_state["saved"] = []; st.rerun()
    st.subheader("What moves the 2047 demand most (one driver at a time)")
    tor = csv("v1_tornado.csv").sort_values("span")
    fig = go.Figure()
    fig.add_bar(y=tor.driver, x=tor.low, orientation="h", name="Low value", marker_color="#B8BFCB")
    fig.add_bar(y=tor.driver, x=tor.high, orientation="h", name="High value", marker_color="#2A7F8F")
    fig.update_layout(barmode="overlay", height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Change vs base, TWh", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True, key="c21")

# ================================================================== VALIDATION
with tabs[5]:
    l, r = st.columns(2)
    with l:
        st.subheader("Backcast: the optimiser on FY26's fleet and demand")
        bk = csv("backcast_fy26.csv"); n_ = bk[bk.region == "India"].set_index("source")
        fig = go.Figure()
        fig.add_bar(x=[LAB[s] for s in SRC], y=n_.loc[SRC, "actual_twh"], name="Actual (CEA)", marker_color="#B8BFCB")
        fig.add_bar(x=[LAB[s] for s in SRC], y=n_.loc[SRC, "model_twh"], name="Model", marker_color="#3A86C8")
        fig.update_layout(barmode="group", height=330, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="TWh", legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True, key="c22")
        st.caption("Regional coal is placed within 6% of national coal. Gas runs on contracts in reality, which a least-cost model does not see.")
        st.dataframe(bk[bk.source == "coal"].drop(columns="source").set_index("region"), use_container_width=True, key="c23")
    with r:
        st.subheader("Against official and published numbers")
        st.dataframe(pd.read_csv(OUT / "dash" / "benchmarks.csv"), use_container_width=True, hide_index=True)
        st.subheader("Income elasticity: four specifications")
        st.dataframe(csv("panel_coefficients.csv"), use_container_width=True, hide_index=True)
        st.caption("Realised FY18→FY26 elasticity: 0.694. Out-of-sample error FY24–26: regression 9.2%, gradient boosting 16.3%, last-value 8.8%.")
    st.subheader("Demand model tests")
    st.dataframe(csv("v1_tests.csv"), use_container_width=True, hide_index=True)

# ================================================================== ASSUMPTIONS
with tabs[6]:
    a = pd.read_csv(OUT / "dash" / "assumptions.csv")
    q = st.text_input("Search assumptions")
    st.dataframe(a[a.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)] if q else a, use_container_width=True, hide_index=True)
    l, r = st.columns(2)
    with l:
        st.subheader("Resource potential vs base 2047 use (GW)")
        st.dataframe(pd.read_csv(OUT / "dash" / "resources_vs_use.csv").set_index("region"), use_container_width=True, key="c24")
    with r:
        st.subheader("Data sources")
        st.dataframe(pd.read_csv(OUT / "dash" / "sources.csv"), use_container_width=True, hide_index=True)
    st.info("AI tools: built with help from Claude (Anthropic) for data gathering, coding and drafting, as the competition terms require us to disclose. "
            "All numbers come from the cited sources and the team's own reproducible model runs.")
