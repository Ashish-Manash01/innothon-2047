"""Visual layer for the dashboard: night-grid theme, India maps (3D regions + state choropleth), Plotly template.

Design: the subject is India's power grid seen at dusk, the hour the system peaks. A deep-navy base lets the six
generation sources carry all the colour; the 3D map of the five CEA regions, extruded by what each generates and
linked by arcs for power traded between them, is the one bold element. Everything around it stays quiet.
Type: Sora for headings and numbers, Source Sans 3 for reading text.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pydeck as pdk
import streamlit as st

GEO = Path(__file__).parent / "data" / "geo"

INK, PANEL, LINE, TEXT, MUTED = "#0D1626", "#142238", "#24364F", "#E8EEF7", "#93A3BA"
COL = dict(coal="#8C96A6", gas="#D08A4E", nuclear="#A88BFA", hydro="#4F9BF5", solar="#F5B83D", wind="#3CC5A8",
           bess="#F07EA0", psp="#7FB2E5")
REGCOL = {"Northern": "#F5B83D", "Western": "#E07A5F", "Southern": "#3CC5A8", "Eastern": "#8C96A6", "North-Eastern": "#4F9BF5"}
# Load-weighted hubs used as arc endpoints (approximate centres of each region's demand)
HUB = {"Northern": (76.8, 27.6), "Western": (75.2, 21.2), "Southern": (78.3, 13.6), "Eastern": (86.2, 23.4), "North-Eastern": (92.6, 26.0)}


def hex_rgb(h, a=255):
    h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a]


CSS = f"""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stMarkdown, .stCaption, p, li, label {{ font-family: 'Source Sans 3', system-ui, sans-serif; }}
h1, h2, h3, [data-testid="stMetricValue"] {{ font-family: 'Sora', system-ui, sans-serif !important; letter-spacing: -0.01em; }}
.block-container {{ padding-top: 1.6rem; max-width: 1480px; }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #111D31 0%, {INK} 100%); border-right: 1px solid {LINE}; }}
[data-testid="stMetric"] {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 14px; padding: 14px 16px 12px; }}
[data-testid="stMetricValue"] {{ font-size: 1.4rem; color: {TEXT}; }}
[data-testid="stMetricLabel"] p {{ font-size: 0.85rem; color: {MUTED}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ font-family: 'Sora', sans-serif; font-size: 0.92rem; padding: 10px 14px; color: {MUTED}; }}
.stTabs [aria-selected="true"] {{ color: {TEXT}; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 10px; }}
.hero h1 {{ font-size: clamp(1.9rem, 2.6vw, 2.7rem); line-height: 1.08; font-weight: 700; margin: 0 0 0.6rem; color: {TEXT}; }}
.hero p.lede {{ font-size: 1.12rem; line-height: 1.55; color: #C3CEDD; max-width: 34rem; margin: 0 0 1.4rem; }}
.hero .facts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; border-top: 1px solid {LINE}; max-width: 36rem; }}
.hero .facts div {{ padding: 14px 16px 4px 0; }}
.hero .facts b {{ display: block; white-space: nowrap; font-family: 'Sora', sans-serif; font-size: 1.3rem; color: {TEXT}; font-weight: 600; }}
.hero .facts span {{ font-size: 0.9rem; color: {MUTED}; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.88rem; color: {MUTED}; margin-top: 6px; }}
.legend i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }}
a {{ color: {COL['solar']}; }}
:focus-visible {{ outline: 2px solid {COL['solar']} !important; outline-offset: 2px; }}
@media (max-width: 760px) {{ .hero .facts {{ grid-template-columns: 1fr; }} }}
</style>
"""


def setup():
    st.markdown(CSS, unsafe_allow_html=True)
    t = go.layout.Template()
    t.layout = go.Layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="Source Sans 3, sans-serif", color=TEXT, size=13),
                         xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
                         yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
                         legend=dict(bgcolor="rgba(0,0,0,0)"), hoverlabel=dict(bgcolor=PANEL, bordercolor=LINE, font_color=TEXT),
                         colorway=[COL[k] for k in ("hydro", "solar", "wind", "nuclear", "gas", "coal")])
    pio.templates["nightgrid"] = t
    pio.templates.default = "plotly_dark+nightgrid"


@st.cache_data
def _geo(name):
    return json.loads((GEO / name).read_text())


def legend(items):
    """items: list of (label, hex)."""
    return '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{l}</span>' for l, c in items) + "</div>"


def grid_map_3d(G, demand, flows, src, lab, height=520, key=None, scale=150):
    """G: region x source TWh; demand: region requirement TWh; flows: Series (from, to) -> TWh."""
    gj = json.loads(json.dumps(_geo("india_regions.geojson")))
    tot = G.sum(axis=1)
    for f in gj["features"]:
        r = f["properties"]["region"]; g = G.loc[r]
        top = g.idxmax()
        net = tot[r] - demand[r]
        f["properties"].update(
            gen=float(tot[r]), elev=float(tot[r]) * scale, color=hex_rgb(REGCOL[r], 215),
            line=hex_rgb("#0D1626", 255),
            tip=(f"<b style='font-family:Sora'>{r}</b><br/>Generates {tot[r]:,.0f} TWh · needs {demand[r]:,.0f} TWh<br/>"
                 f"{'Exports' if net >= 0 else 'Imports'} {abs(net):,.0f} TWh<br/>"
                 + "<br/>".join(f"{lab[s]}: {g[s] / tot[r] * 100:.0f}%" for s in src if g[s] / tot[r] > 0.005)))
    poly = pdk.Layer("GeoJsonLayer", gj, extruded=True, wireframe=False, get_elevation="properties.elev",
                     get_fill_color="properties.color", get_line_color="properties.line", line_width_min_pixels=1,
                     pickable=True, auto_highlight=True, highlight_color=[255, 255, 255, 60],
                     material={"ambient": 0.45, "diffuse": 0.6, "shininess": 24, "specularColor": [255, 240, 210]})
    # net flow between each pair, drawn from exporter to importer
    net = {}
    for (a, b), v in flows.items():
        if a == b:
            continue
        k = tuple(sorted((a, b))); s = v if (a, b) == k else -v
        net[k] = net.get(k, 0) + s
    arcs = []
    for (a, b), v in net.items():
        if abs(v) < 10:
            continue
        fr, to = (a, b) if v > 0 else (b, a)
        arcs.append({"src": [*HUB[fr], float(tot[fr]) * scale + 2000], "dst": [*HUB[to], float(tot[to]) * scale + 2000], "w": max(abs(v) / 14, 2.5), "tip": f"<b>{fr} → {to}</b><br/>{abs(v):,.0f} TWh a year"})
    arc = pdk.Layer("ArcLayer", pd.DataFrame(arcs) if arcs else pd.DataFrame(columns=["src", "dst", "w", "tip"]),
                    get_source_position="src", get_target_position="dst", get_width="w",
                    get_source_color=hex_rgb("#FFFFFF", 255), get_target_color=hex_rgb("#F5B83D", 230),
                    get_height=0.9, get_tilt=0, pickable=True, width_min_pixels=2, great_circle=False)
    view = pdk.ViewState(latitude=20.2, longitude=81.8, zoom=3.45, pitch=40, bearing=-8)
    deck = pdk.Deck(layers=[poly, arc], initial_view_state=view, map_provider="carto", map_style=pdk.map_styles.CARTO_DARK_NO_LABELS,
                    tooltip={"html": "{tip}", "style": {"background": PANEL, "color": TEXT, "border": f"1px solid {LINE}",
                                                        "font-family": "Source Sans 3", "font-size": "13px", "border-radius": "8px"}})
    st.pydeck_chart(deck, height=height, key=key)


def region_choropleth(states, values=None, title="", fmt=lambda v: f"{v:,.0f}", height=440):
    """State map. values=None -> coloured by CEA region; else a dict code -> value (continuous)."""
    gj = _geo("india_states.geojson")
    s = states.set_index("code")
    codes = [f["id"] for f in gj["features"]]
    names = {f["id"]: f["properties"]["name"] for f in gj["features"]}
    fig = go.Figure()
    if values is None:
        for r, c in REGCOL.items():
            cs = [k for k in codes if s.loc[k, "cea_region"] == r]
            fig.add_trace(go.Choropleth(geojson=gj, locations=cs, z=[1] * len(cs), featureidkey="id", name=r,
                                        colorscale=[[0, c], [1, c]], showscale=False, marker_line_color=INK, marker_line_width=0.8,
                                        text=[names[k] for k in cs], hovertemplate="%{text}<br>" + r + " region<extra></extra>"))
    else:
        z = [values.get(k) for k in codes]
        fig.add_trace(go.Choropleth(geojson=gj, locations=codes, z=z, featureidkey="id", colorscale="YlOrBr",
                                    marker_line_color=INK, marker_line_width=0.8, colorbar=dict(title=title, thickness=10),
                                    text=[names[k] for k in codes], hovertemplate="%{text}: %{z:,.2f}<extra></extra>"))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    return fig
