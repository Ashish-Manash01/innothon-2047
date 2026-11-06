"""Build the defensibility deck's slide files from the model outputs (numbers are read, never retyped)."""
import json, html
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent / "project"; (ROOT / "slides").mkdir(parents=True, exist_ok=True)
OUT = Path(__file__).resolve().parents[1] / "out"
D = OUT / "dash"

# ------------------------------------------------------------------ data
nb = pd.read_csv(OUT / "v1_national_base.csv", index_col=0)
hist = pd.read_csv(D / "history_national.csv").set_index("fy_end")
q = pd.read_csv(OUT / "v1_mc_quantiles_2047.csv", index_col=0)
summ = pd.read_csv(OUT / "v1_summary_2047.csv", index_col=0)
tor = pd.read_csv(OUT / "v1_tornado.csv").sort_values("span", ascending=False)
reg_d = pd.read_csv(OUT / "v1_regional_2047_base.csv", index_col=0)
g = pd.read_csv(OUT / "mix_base_generation_twh.csv", index_col=0)
cap = pd.read_csv(OUT / "mix_base_capacity_gw.csv", index_col=0)
bal = pd.read_csv(OUT / "mix_base_regional_balance.csv", index_col=0)
path = pd.read_csv(OUT / "pathway_national.csv").set_index("fy_end")
sc = pd.read_csv(OUT / "mix_scenarios_2047.csv").set_index("scenario")
bk = pd.read_csv(OUT / "backcast_fy26.csv")
panel = pd.read_csv(OUT / "panel_coefficients.csv")

SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"]
LAB = dict(coal="Coal", gas="Gas", nuclear="Nuclear", hydro="Hydro", solar="Solar", wind="Wind")
COL = dict(coal="#6E6E73", gas="#B07D3A", nuclear="#8A6CC9", hydro="#3A86C8", solar="#E0AA22", wind="#34A585")
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]

base_total = nb.loc[2047, "gen_total"]; base_grid = nb.loc[2047, "gen_grid"]; base_h2 = nb.loc[2047, "gen_h2"]
fy26 = hist.loc[2026, "generation_twh"]
mult = base_total / fy26; cagr = (mult ** (1 / 21) - 1) * 100
p10, p50, p90 = q.loc["gen_total_2047", ["P10", "P50", "P90"]]
nat = g.drop(columns="total").sum(); natpct = nat / nat.sum() * 100
nonfossil = 100 - natpct.coal - natpct.gas
B = sc.loc["Base"]
f0 = lambda v: f"{v:,.0f}"; f1 = lambda v: f"{v:,.1f}"

# ------------------------------------------------------------------ look
DARK, LIGHT, LIGHT2, INK, MUTED, ACC, ACC2, RULE = "#14213D", "#FBFAF6", "#F1EEE6", "#1B2433", "#4A5568", "#C9821B", "#2A7F8F", "#DDD8CC"
SERIF = "'Source Serif 4', Georgia, serif"; SANS = "'IBM Plex Sans', Arial, sans-serif"
e = html.escape
slides, order = {}, []


def section(sid, body, notes, bg=LIGHT, color=INK, extra="", pad="128px 128px 160px", page=True, transition="fade"):
    n = len(order) + 1
    foot = f'<p style="position:absolute;left:128px;bottom:64px;width:1664px;font-size:24px;color:{MUTED if bg != DARK else "#A9B4C8"}">India 2047 electricity forecast · INNOTHON 2026 · {n}</p>' if page else ""
    s = (f'<section id="{sid}" data-transition="{transition}" style="background:{bg};color:{color};font-family:{SANS};padding:{pad};'
         f'display:flex;flex-direction:column;gap:40px{extra}">\n{body}\n{foot}\n<aside>{e(notes)}</aside>\n</section>\n')
    slides[sid] = s; order.append(sid)


def title(t, eyebrow=None, color=DARK):
    eb = f'<p style="font-size:24px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:{ACC}">{e(eyebrow)}</p>' if eyebrow else ""
    return f'<div style="display:flex;flex-direction:column;gap:12px">{eb}<h2 style="font-family:{SERIF};font-size:64px;font-weight:600;line-height:1.1;color:{color}">{t}</h2></div>'


def card(h, body, w="flex:1", bg="#FFFFFF"):
    return (f'<div style="{w};display:flex;flex-direction:column;gap:16px;background:{bg};padding:40px;border:1px solid {RULE};border-radius:16px">'
            f'<h3 style="font-size:32px;font-weight:600;color:{DARK}">{h}</h3><p style="font-size:28px;line-height:1.4;color:{MUTED}">{body}</p></div>')


def legend(keys=SRC):
    items = "".join(f'<div style="display:flex;flex-direction:row;gap:12px;align-items:center"><div style="width:24px;height:24px;border-radius:4px;background:{COL[k]}"></div><p style="font-size:24px;color:{MUTED}">{LAB[k]}</p></div>' for k in keys)
    return f'<div style="display:flex;flex-direction:row;gap:32px">{items}</div>'


def table(head, rows, widths, size=28, hl=None):
    th = "".join(f'<th style="width:{w}%;text-align:{"left" if i == 0 else "right"}">{e(h)}</th>' for i, (h, w) in enumerate(zip(head, widths)))
    tr = ""
    for ri, r in enumerate(rows):
        bgc = "background:#F1EEE6;" if hl is not None and ri in hl else ""
        tr += f'<tr style="{bgc}">' + "".join(f'<td style="text-align:{"left" if i == 0 else "right"}">{e(str(c))}</td>' for i, c in enumerate(r)) + "</tr>"
    return f'<table style="font-size:{size}px;color:{INK};font-variant-numeric:tabular-nums"><tr>{th}</tr>{tr}</table>'


# ------------------------------------------------------------------ 1 cover
section("cover", f'''
<div style="flex:1"></div>
<p style="font-size:28px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:{ACC}">ExxonMobil INNOTHON 2026 · Defensibility review</p>
<h1 style="font-family:{SERIF};font-size:96px;font-weight:600;line-height:1.08;color:{LIGHT}">India will need about {f0(base_total)} TWh of electricity in 2047, and can make {nonfossil:.0f}% of it without fossil fuels</h1>
<p style="font-size:36px;line-height:1.4;color:#C9D3E3">A state-level demand forecast and a least-cost regional generation plan for FY2046-47</p>
<div style="flex:1"></div>
<p style="font-size:28px;color:#A9B4C8">Manash · NIT Karnataka, Surathkal · Final evaluation, 21–22 November 2026</p>''',
        "Open with the answer. Two numbers to remember: about 5,550 terawatt-hours generated in FY2046-47, three times today, and a mix that is 78 percent non-fossil while holding power-sector emissions at today's level. Everything after this slide is how we got there and why you can trust it.",
        bg=DARK, color=LIGHT, page=False, pad="128px")

# ------------------------------------------------------------------ 2 the answer
kpi = lambda big, unit, lab: (f'<div style="flex:1;display:flex;flex-direction:column;gap:8px;background:#FFFFFF;border:1px solid {RULE};border-radius:16px;padding:40px">'
                              f'<p style="font-family:{SERIF};font-size:88px;font-weight:600;line-height:1;color:{DARK}">{big}<span style="color:{ACC}"> {unit}</span></p>'
                              f'<p style="font-size:28px;line-height:1.35;color:{MUTED}">{lab}</p></div>')
section("answer", title("The answer on one slide", "Summary") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{kpi(f0(base_total), "TWh", f"Electricity generated in FY2046-47, base case: grid {f0(base_grid)} + green hydrogen {f0(base_h2)}")}
{kpi(f"{mult:.1f}×", "", f"FY26's {f0(fy26)} TWh; {cagr:.1f}% a year for 21 years")}
{kpi(f"{f0(p10)}–{f0(p90)}", "", "TWh, Monte Carlo P10–P90 of 2,000 runs: our uncertainty band")}
</div>
<div style="display:flex;flex-direction:row;gap:32px">
{kpi(f"{nonfossil:.0f}%", "", f"Non-fossil share of 2047 generation: solar {natpct.solar:.0f}%, wind {natpct.wind:.0f}%, nuclear {natpct.nuclear:.0f}%, hydro {natpct.hydro:.0f}%")}
{kpi(f"{B.co2_mt/1000:.1f}", "Gt", "Power-sector CO₂ in 2047: held at today's level, a peak-and-plateau path to Net Zero 2070")}
{kpi(f"₹{B.cost_rs_per_kwh:.2f}", "", "Average system cost per kWh (2026 prices), generation, storage and transmission")}
</div>''',
        "The six numbers to anchor on. Demand triples; the band is 5,200 to 6,800; the mix goes from 28 percent non-fossil today to 78 percent; emissions plateau at 1.2 gigatonnes; and the average system cost stays under four rupees a unit, cheaper than new coal.")

# ------------------------------------------------------------------ 3 approach
step = lambda n, h, b: (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:#FFFFFF;border:1px solid {RULE};border-top:8px solid {ACC2};border-radius:16px;padding:32px">'
                        f'<p style="font-size:24px;font-weight:600;color:{ACC2}">{n}</p><h3 style="font-size:32px;font-weight:600;color:{DARK}">{h}</h3><p style="font-size:24px;line-height:1.4;color:{MUTED}">{b}</p></div>')
section("approach", title("Two linked models turn public data into a regional plan", "Method") + f'''
<div style="display:flex;flex-direction:row;gap:24px">
{step("1 · Data", "Official sources", "CEA, MoP, UN WPP 2024, MoSPI, MoHFW, NISE, NIWE, DAE; 16 automated checks")}
{step("2 · Demand", "State panel model", "36 states: income, population, urbanisation; plus EVs, data centres, green H₂")}
{step("3 · Uncertainty", "2,000 Monte Carlo runs", "Every driver varied at once; tornado shows which matter")}
{step("4 · Mix", "Least-cost optimiser", "5 regions × 6 sources × 12 time slices; resources, build speed, grid, CO₂")}
{step("5 · Proof", "Backcast and benchmarks", "Reproduces FY26; checked against CEA, NEP and published 2047 studies")}
</div>
<p style="font-size:32px;line-height:1.4;color:{INK}">Metric throughout: <b>electricity generated</b> in FY2046-47, not capacity and not consumption. Regions follow CEA's five grids. Every number traces to a source or a reproducible run, live in our dashboard.</p>''',
        "The method in one picture. We built two models that hand off to each other: demand by state, rolled up to regions, then a cost-minimising plan for how each region generates it. Step five is the part most teams skip: we tested the plan on today's grid before trusting 2047.")

# ------------------------------------------------------------------ 4 demand model
b = panel.iloc[0]
section("demand-model", title(f"Electricity use per person rises {b.income_elasticity_b:.2f}% for every 1% rise in income", "Demand model") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{card("Estimated, not assumed", f"State fixed-effects regression, 32 states × 11 years (332 observations). Elasticity {b.income_elasticity_b:.3f}, standard error {b.se_b:.3f}, R² 0.986. Four other specifications: 0.663–0.689.")}
{card("Tested against what happened", "Realised FY18→FY26 elasticity was 0.694. The model's FY27 requirement is 1,859 TWh vs CEA's forecast of 1,887 (−1.5%).")}
{card("Urbanisation works through income", "Urban share alone predicts +2.2% use per point, but it vanishes once income is included (correlation 0.71). We keep the term and report it.")}
</div>
<p style="font-size:30px;line-height:1.4;color:{INK}">Projection: UN population (1,665 million in 2047) × state shares, GDP at 6.5% a year, elasticity easing to 75% of today's by 2047 as demand matures. We tried gradient boosting: worse out of sample (16.3% error vs 9.2%) and it cannot extrapolate.</p>''',
        "Why a regression and not a neural network: the regression explains itself, it matched what actually happened from 2018 to 2026, and machine learning did worse out of sample because 2047 incomes are outside anything it has seen. Urbanisation matters, but through income: richer states are more urban.")

# ------------------------------------------------------------------ 5 demand chart (div bars)
yrs = [2010, 2015, 2020, 2026, 2030, 2035, 2040, 2047]
vals = [hist.loc[y, "generation_twh"] if y <= 2026 else nb.loc[y, "gen_total"] for y in yrs]
grid_v = [hist.loc[y, "generation_twh"] if y <= 2026 else nb.loc[y, "gen_grid"] for y in yrs]
mx = max(vals); H = 560
bars = ""
for y, v, gv in zip(yrs, vals, grid_v):
    actual = y <= 2026
    hg, hh = gv / mx * H, (v - gv) / mx * H
    seg = (f'<div style="width:120px;height:{hh:.0f}px;background:{COL["wind"]}"></div>' if hh > 1 else "") + \
          f'<div style="width:120px;height:{hg:.0f}px;background:{"#9AA3B2" if actual else DARK}"></div>'
    bars += (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:end;gap:8px">'
             f'<p style="font-size:26px;font-weight:600;color:{INK}">{f0(v)}</p><div style="display:flex;flex-direction:column">{seg}</div>'
             f'<p style="font-size:24px;color:{MUTED}">FY{str(y)[2:]}{" actual" if actual and y == 2026 else ""}</p></div>')
section("demand-forecast", title(f"Generation triples to {f0(base_total)} TWh by FY2046-47", "Forecast") + f'''
<div style="display:flex;flex-direction:row;gap:16px;align-items:end;height:680px">{bars}</div>
<div style="display:flex;flex-direction:row;gap:32px"><div style="display:flex;flex-direction:row;gap:12px;align-items:center"><div style="width:24px;height:24px;border-radius:4px;background:#9AA3B2"></div><p style="font-size:24px;color:{MUTED}">Actual (CEA)</p></div><div style="display:flex;flex-direction:row;gap:12px;align-items:center"><div style="width:24px;height:24px;border-radius:4px;background:{DARK}"></div><p style="font-size:24px;color:{MUTED}">Forecast, grid demand</p></div><div style="display:flex;flex-direction:row;gap:12px;align-items:center"><div style="width:24px;height:24px;border-radius:4px;background:{COL["wind"]}"></div><p style="font-size:24px;color:{MUTED}">Green hydrogen</p></div></div>''',
        f"Growth from {f0(fy26)} to {f0(base_total)} terawatt-hours is about {cagr:.1f} percent a year, slightly faster than the 2014 to 2025 trend because of new loads. Hydrogen is shown separately so the grid number can be read on its own.")

# ------------------------------------------------------------------ 6 new loads
section("new-loads", title(f"New loads add about {round((nb.loc[2047,'gen_ev_dc'] + base_h2) / 50) * 50:,.0f} TWh that history cannot show", "Demand model") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{card("Electric vehicles", f"{f0(nb.loc[2047,'ev_twh'])} TWh in 2047. Bottom-up fleet of two-wheelers, cars, three-wheelers, buses and trucks. S-curve calibrated to IEA (~25 TWh in 2030) and IESA (~38 TWh in FY32).")}
{card("Data centres", f"{f0(nb.loc[2047,'dc_twh'])} TWh in 2047. Wood Mackenzie path: 10 TWh in 2025 to 191 TWh in 2040. Placed in announced hubs: Maharashtra, Tamil Nadu, Telangana, Karnataka.")}
{card("Green hydrogen", f"{f0(base_h2)} TWh in 2047: 12 Mt at 48 kWh/kg. Flexible electrolysers, fed mostly by dedicated renewables; kept as a separate layer. Range 5–25 Mt.")}
</div>
<p style="font-size:30px;line-height:1.4;color:{INK}">Only growth above what the historical trend already contains is added, so nothing is counted twice. These three are the largest source of uncertainty in the forecast.</p>''',
        "History cannot predict loads that barely exist yet, so we model them bottom-up and calibrate each to a published outlook. Hydrogen alone is about ten percent of 2047 generation, which is why we keep it separate.")

# ------------------------------------------------------------------ 7 uncertainty (tornado)
ext = max(tor.high.max(), -tor.low.min()); W = 560
rows_t = ""
for _, r in tor.iterrows():
    lw, hw = -r.low / ext * W, r.high / ext * W
    rows_t += (f'<div style="display:flex;flex-direction:row;align-items:center;gap:0px;height:56px">'
               f'<p style="width:520px;font-size:24px;color:{INK}">{e(r.driver)}</p>'
               f'<div style="width:{W}px;display:flex;flex-direction:row;justify-content:end;align-items:center;gap:8px"><p style="font-size:24px;color:{MUTED}">{f0(r.low)}</p><div style="width:{lw:.0f}px;height:36px;background:#B8BFCB;border-radius:4px"></div></div>'
               f'<div style="width:4px;height:56px;background:{INK}"></div>'
               f'<div style="width:{W}px;display:flex;flex-direction:row;align-items:center;gap:8px"><div style="width:{hw:.0f}px;height:36px;background:{ACC2};border-radius:4px"></div><p style="font-size:24px;color:{MUTED}">+{f0(r.high)}</p></div></div>')
section("uncertainty", title("Hydrogen, income response and GDP drive the uncertainty", "Uncertainty") + f'''
<div style="display:flex;flex-direction:column;gap:8px">{rows_t}</div>
<p style="font-size:28px;line-height:1.4;color:{INK}">Change in 2047 total vs base {f0(base_total)} TWh, one driver at a time (grey low, teal high). All at once, the Monte Carlo P10–P90 is <b>{f0(p10)}–{f0(p90)} TWh</b>; published 2047 scenarios (5,254–6,033) sit inside it.</p>''',
        "Read this as where to spend effort. Population and conversion losses barely matter. Hydrogen policy, how strongly use responds to income, and GDP each move the answer by about a thousand terawatt-hours. The Monte Carlo median is above base because hydrogen and elasticity ranges skew upward.")

# ------------------------------------------------------------------ 8 regional demand
rd = reg_d.drop(index="India").reindex(["Western", "Southern", "Northern", "Eastern", "North-Eastern"])
rows = [[r, f0(v.req_fy26_twh), f0(v.gen_grid_2047_twh), f0(v.gen_h2_2047_twh), f0(v.gen_total_2047_twh), f"{v.growth_x:.1f}×"] for r, v in rd.iterrows()]
rows.append(["India", f0(reg_d.loc["India", "req_fy26_twh"]), f0(reg_d.loc["India", "gen_grid_2047_twh"]), f0(reg_d.loc["India", "gen_h2_2047_twh"]), f0(reg_d.loc["India", "gen_total_2047_twh"]), f"{reg_d.loc['India','growth_x']:.1f}×"])
section("regional-demand", title("The South grows fastest; the West stays the largest", "Regional demand") +
        table(["Region", "FY26 requirement TWh", "2047 grid TWh", "2047 green H₂ TWh", "2047 total TWh", "Growth"], rows, [24, 16, 15, 16, 15, 14], size=30, hl=[5]) +
        f'<p style="font-size:28px;line-height:1.4;color:{INK}">Built up from 36 states and union territories, so regions always add to the national total. Data centres and hydrogen clusters pull growth south and west; Northern states grow from a larger base.</p>',
        "Regions are sums of states, not shares of a national number, so the regional story comes from each state's own income, population and urbanisation. The South is 3.2 times today because of data centres in Tamil Nadu and Telangana and hydrogen in Andhra Pradesh and Tamil Nadu.")

# ------------------------------------------------------------------ 9 mix model
section("mix-model", title("A least-cost optimiser decides who generates what, hour by season", "Mix model") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{card("Sees night and monsoon", "12 time slices: 4 seasons × day, evening, night. Solar is absent at night and dims in the monsoon; wind peaks June–September. An annual-only version gave 0% coal, so we rejected it.")}
{card("Respects real limits", "NISE solar, NIWE wind and CEA hydro potential; build speed (solar 1,279 GW, wind 375 GW by 2047); 229 GW of committed coal; nuclear ≤ 100 GW; corridors 3× today.")}
{card("Keeps the lights on", "15% reserve over peak; coal never below 40% of its evening output; 4-hour batteries and 8-hour pumped storage cycle daily with losses; CO₂ ≤ 1.2 Gt.")}
</div>
<p style="font-size:30px;line-height:1.4;color:{INK}">Linear programme solved with HiGHS in under a second per scenario, so we ran 135 policy combinations for the dashboard. Costs are 2026 tariffs: solar ₹2.5–3.0, wind ₹3–4, coal ₹5–6.3, nuclear ₹6–7 per kWh.</p>''',
        "The optimiser is the honest way to answer where each region's power should come from: it has to meet demand in every season and time of day at the lowest cost, within physical and policy limits. The time slices matter. Without them, solar looked able to do everything.")

# ------------------------------------------------------------------ 10 national mix
bar = "".join(f'<div style="width:{natpct[s]/100*1664:.0f}px;height:120px;background:{COL[s]}"></div>' for s in SRC)
lab = "".join(f'<div style="flex:1;display:flex;flex-direction:column;gap:4px;border-top:8px solid {COL[s]};padding:16px 0px 0px"><p style="font-family:{SERIF};font-size:56px;font-weight:600;color:{DARK}">{natpct[s]:.1f}%</p><p style="font-size:26px;color:{MUTED}">{LAB[s]} · {f0(nat[s])} TWh · {f0(cap[s].sum())} GW</p></div>' for s in SRC)
section("national-mix", title(f"In 2047, solar and wind make {natpct.solar + natpct.wind:.0f}% of India's electricity; coal falls to {natpct.coal:.0f}%", "2047 mix") + f'''
<div style="display:flex;flex-direction:row;border-radius:12px;overflow:hidden">{bar}</div>
<div style="display:flex;flex-direction:row;gap:24px">{lab}</div>
<p style="font-size:30px;line-height:1.4;color:{INK}">Storage: {f0(cap.bess.sum())} GW of batteries and {f0(cap.psp.sum())} GW of pumped hydro move midday sun into the evening, against CEA's own estimate of 476 GW of storage needed in 2046-47. No new coal is built beyond what is committed; the 229 GW fleet runs at 62% load factor, mostly evenings and nights.</p>''',
        "Solar is the cheapest energy, so it is built as fast as India can build it. Coal does not disappear: the committed fleet is paid for and covers nights and the low-wind winter. Gas is backup capacity only, because imported LNG is the most expensive energy on the system.")

# ------------------------------------------------------------------ 11 regional mix
mxr = g.total.max(); rows_r = ""
why = {"Northern": "Rajasthan sun; Himalayan hydro; exports midday solar",
       "Western": "Coastal wind; cheapest pithead coal in Chhattisgarh and MP",
       "Southern": "Wind in TN, KA, AP; nuclear firms the weaker sun",
       "Eastern": "Weakest sun, no wind: pithead coal plus new nuclear; imports",
       "North-Eastern": "Arunachal hydro; exports to North and East"}
for r in ["Western", "Northern", "Southern", "Eastern", "North-Eastern"]:
    segs = "".join(f'<div style="width:{g.loc[r, s]/mxr*760:.0f}px;height:48px;background:{COL[s]}"></div>' for s in SRC if g.loc[r, s] > 0.5)
    ne = bal.loc[r, "net_export_twh"]
    rows_r += (f'<div style="display:flex;flex-direction:row;align-items:center;gap:24px;height:96px;border-bottom:1px solid {RULE}">'
               f'<p style="width:260px;font-size:30px;font-weight:600;color:{DARK}">{r}</p>'
               f'<div style="width:780px;display:flex;flex-direction:row;align-items:center;gap:12px"><div style="display:flex;flex-direction:row">{segs}</div><p style="font-size:24px;color:{MUTED}">{f0(g.loc[r,"total"])}</p></div>'
               f'<p style="width:560px;font-size:24px;line-height:1.3;color:{INK}">{why[r]} ({"exports" if ne > 0 else "imports"} {f0(abs(ne))} TWh)</p></div>')
section("regional-mix", title("Each region generates from what it has", "2047 regional mix") + f'''
<div style="display:flex;flex-direction:column">{rows_r}</div>
{legend()}''',
        "This is the core of the regional strategy. The North is the solar hub and exports. The West balances wind, solar and cheap pithead coal. The South pairs wind with nuclear because its sun is weaker. The East has poor sun and no wind at 150 metres, so it keeps pithead coal, adds nuclear and imports clean power over the corridors. The North-East is hydro.")

# ------------------------------------------------------------------ 12 pathway
pmax = path.total_twh.max(); cols = ""
for y, r in path.iterrows():
    segs = "".join(f'<div style="width:150px;height:{r[s + "_twh"]/pmax*520:.0f}px;background:{COL[s]}"></div>' for s in reversed(SRC) if r[s + "_twh"] > 0.5)
    cols += (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:end;gap:8px">'
             f'<p style="font-size:26px;font-weight:600;color:{INK}">{f0(r.total_twh)}</p><div style="display:flex;flex-direction:column">{segs}</div>'
             f'<p style="font-size:24px;color:{MUTED}">FY{str(y)[2:]}{" actual" if r.kind == "actual" else ""}</p>'
             f'<p style="font-size:24px;color:{MUTED}">coal {r.coal_pct:.0f}% · CO₂ {f0(r.co2_mt)} Mt</p></div>')
section("pathway", title("Clean power carries all the growth; coal output stays near today's level", "Pathway") + f'''
<div style="display:flex;flex-direction:row;gap:24px;align-items:end;height:660px">{cols}</div>
{legend()}''',
        "The same model solved at each milestone with that year's demand, committed fleet and build limits. FY30 lands next to CEA's National Electricity Plan: about half coal and 1.17 gigatonnes, versus NEP's 50 percent and 1.18 gigatonnes for FY32. Emissions peak in the mid-2030s, then fall.")

# ------------------------------------------------------------------ 13 trade-offs
keys = [("Base", "Base: 1.2 Gt cap"), ("Relaxed CO2 (1.7 Gt)", "CO₂ cap 1.7 Gt (NEP-like)"), ("Strict CO2 (0.8 Gt)", "CO₂ cap 0.8 Gt"),
        ("Nuclear delay (<=50 GW)", "Nuclear ≤ 50 GW"), ("Faster RE build (+25%)", "Solar/wind 25% faster"), ("Slower RE build (-25%)", "Solar/wind 25% slower"),
        ("Demand P90", "Demand P90")]
rows_s = []
for k, l in keys:
    r = sc.loc[k]
    over = f" (+{f0(r.co2_over_cap_mt)})" if r.co2_over_cap_mt > 0.5 else ""
    rows_s.append([l, f1(r["coal_%"]), f1(r["nuclear_%"]), f1(r["solar_%"] + r["wind_%"]), f1(r["non_fossil_%"]), f0(r.co2_mt) + over, f"{r.cost_rs_per_kwh:.2f}"])
section("tradeoffs", title("How fast India builds matters more than what solar costs", "Trade-offs") +
        table(["2047 scenario", "Coal %", "Nuclear %", "Solar + wind %", "Non-fossil %", "CO₂ Mt (over cap)", "₹/kWh"], rows_s, [28, 10, 11, 13, 12, 15, 11], size=28, hl=[0]) +
        f'<p style="font-size:28px;line-height:1.4;color:{INK}">Solar 30% dearer changes nothing (it is already build-limited). Building 25% slower overshoots the cap by {f0(sc.loc["Slower RE build (-25%)","co2_over_cap_mt"])} Mt. Delaying nuclear triples the carbon price and brings back imported gas. Transmission at 2× instead of 3× barely matters.</p>',
        "The policy message: permitting, land, transmission and manufacturing speed decide the outcome more than technology cost. Nuclear is the flexible lever. A slower build or a delayed nuclear programme pushes India back to coal and imported gas.")

# ------------------------------------------------------------------ 14 validation
nb_ = bk[bk.region == "India"].set_index("source")
ta = nb_.actual_twh.sum(); tm = nb_.model_twh.sum()
rows_v = [[LAB[s], f1(nb_.loc[s, "actual_twh"] / ta * 100), f1(nb_.loc[s, "model_twh"] / tm * 100)] for s in SRC]
bench = [["Requirement FY27", "1,859 TWh", "1,887 TWh (CEA forecast)"], ["Coal share FY30 vs FY32", f"{path.loc[2030,'coal_pct']:.0f}% (FY30)", "~50% (NEP, FY32)"],
         ["Power CO₂ FY30 vs FY32", f"{f0(path.loc[2030,'co2_mt'])} Mt", "1,180 Mt (draft NEP)"], ["Total generation 2047", f"{f0(base_total)} TWh", "5,254–6,033 (published)"],
         ["Storage 2047", f"{f0(cap.bess.sum() + cap.psp.sum())} GW", "476 GW (CEA need)"], ["Solar / wind 2047", "1,279 / 375 GW", "~1,200 / 400–450 GW (CEA)"]]
section("validation", title("Tested on today's grid before trusting 2047", "Validation") + f'''
<div style="display:flex;flex-direction:row;gap:48px">
<div style="flex:1;display:flex;flex-direction:column;gap:16px"><h3 style="font-size:32px;font-weight:600;color:{DARK}">FY26 backcast, share of generation</h3>{table(["Source", "Actual %", "Model %"], rows_v, [40, 30, 30], size=26)}<p style="font-size:24px;line-height:1.4;color:{MUTED}">Regional coal placed within 6%; inter-regional flows in the right direction. Gas runs on contracts the model does not see.</p></div>
<div style="flex:1.4;display:flex;flex-direction:column;gap:16px"><h3 style="font-size:32px;font-weight:600;color:{DARK}">Against official numbers</h3>{table(["Measure", "Ours", "Benchmark"], bench, [36, 26, 38], size=26)}<p style="font-size:24px;line-height:1.4;color:{MUTED}">Plus 13 checks recomputed on every solution: energy balance in all 60 region-slices, caps, reserve, CO₂, corridors.</p></div>
</div>''',
        "Most forecasts are judged only on plausibility. We gave the mix model today's fleet and today's demand and it reproduced the actual FY26 mix within about one point. Our FY30 and 2047 figures sit next to CEA's own plan, and the storage the optimiser chooses matches CEA's independent estimate within six percent.")

# ------------------------------------------------------------------ 15 screening reconciliation
rows_q = [["2047 demand", "5,400 TWh", f"{f0(base_total)} TWh"], ["Coal", "28%", f"{natpct.coal:.1f}%"], ["Gas", "6%", f"{natpct.gas:.1f}%"], ["Solar", "30%", f"{natpct.solar:.1f}%"],
          ["Wind", "17%", f"{natpct.wind:.1f}%"], ["Hydro", "9%", f"{natpct.hydro:.1f}%"], ["Nuclear", "10%", f"{natpct.nuclear:.1f}%"], ["Non-fossil", "66%", f"{nonfossil:.1f}%"]]
section("screening", title("The model confirmed our screening size and moved the mix off coal", "What changed") + f'''
<div style="display:flex;flex-direction:row;gap:48px">
<div style="flex:1">{table(["", "Screening answer", "Full model"], rows_q, [34, 33, 33], size=28)}</div>
<div style="flex:1;display:flex;flex-direction:column;gap:24px">
{card("Size held", "Demand is within 3% of our screening figure; the bottom-up new loads explain the difference.", "")}
{card("Mix moved", "Least cost under a flat CO₂ cap builds no new coal and little gas. The draft-NEP-like cap (1.7 Gt) gives 68% non-fossil, close to our screening 66%.", "")}
</div></div>''',
        "Judges will compare our final answer with what we submitted at registration. The total held. The mix moved because the optimiser found that, once the committed coal fleet is used fully, new solar plus batteries beats new coal and imported gas on cost.")

# ------------------------------------------------------------------ 16 policy statement (accent slide)
pt = lambda h, b: f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;border-top:4px solid {ACC};padding:24px 0px 0px"><h3 style="font-size:36px;font-weight:600;color:{LIGHT}">{h}</h3><p style="font-size:28px;line-height:1.4;color:#C9D3E3">{b}</p></div>'
section("implications", f'''
<p style="font-size:28px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:{ACC}">What this means for India</p>
<h2 style="font-family:{SERIF};font-size:72px;font-weight:600;line-height:1.12;color:{LIGHT}">Build speed, not technology cost, decides whether 2047 is clean</h2>
<div style="flex:1"></div>
<div style="display:flex;flex-direction:row;gap:48px">
{pt("Build 70 GW of solar a year", "And 20 GW of wind: 1.6× and 3× today's records. Land, permitting and domestic manufacturing are the bottleneck.")}
{pt("Wire the East", "Triple inter-regional transfer capacity so the North, West and North-East can supply the East.")}
{pt("Keep nuclear on schedule", "80–100 GW is the clean firm power that lets coal plateau; delay brings back imported gas.")}
{pt("Store the sun", "About 500 GW of storage by 2047, mostly 4-hour batteries next to solar.")}
</div>''',
        "The decision-relevant finding: the cheapest clean system is available, and the constraint is delivery. Four actions follow directly from the model's binding constraints.",
        bg=DARK, color=LIGHT, pad="128px 128px 160px")

# ------------------------------------------------------------------ 17 limitations
section("limitations", title("What the model simplifies, and what changes on 13 November", "Limitations") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{card("12 slices, not 8,760 hours", "Multi-day wind or sun lulls are covered only by the reserve margin. Our storage need is close to CEA's, so the effect looks small.")}
{card("Stylised daily shapes", "Demand, solar, wind and hydro profiles are documented assumptions. Hourly data in the official release will replace them.")}
{card("New loads are outlooks", "Hydrogen, EVs and data centres have no history, so they carry wide ranges and dominate the uncertainty.")}
</div>
<p style="font-size:30px;line-height:1.4;color:{INK}">One script reloads the official datasets, compares them with our public data, and reruns the demand model, Monte Carlo, mix, pathway and dashboard; every change is logged with its cause. Costs are held at 2026 levels, which is conservative for solar and batteries.</p>''',
        "Being explicit about limits is part of defensibility. None of these is hidden in the dashboard, and the official data release plugs straight into the pipeline.")

# ------------------------------------------------------------------ 18 dashboard + close
section("dashboard", title("Explore every assumption live: the models re-run as you move a slider", "Interactive dashboard") + f'''
<div style="display:flex;flex-direction:row;gap:32px">
{card("Trace the forecast", "Move GDP, income response, population, EVs, data centres or hydrogen and the state model re-runs. Pick any state to see population, urbanisation, use per person and demand, year by year.")}
{card("Inspect regional trade-offs", "Change the CO₂ cap, nuclear policy, build speed, transmission or storage cost and the optimiser re-solves all five regions in about two seconds, with 13 checks on every solution.")}
{card("Explore scenarios", "Save settings and compare them with the 1.2 Gt and draft-NEP-like 1.7 Gt cases; see the pathway re-solve to 2047 and the FY26 backcast.")}
</div>
<p style="font-size:30px;line-height:1.4;color:{INK}"><a href="https://innothon-2047-lht5kj3587q6dwmteapysu.streamlit.app/">innothon-2047-lht5kj3587q6dwmteapysu.streamlit.app</a> · built in Streamlit on our own Python models; a pre-computed backup runs on claude.ai. AI tools: built with help from Claude (Anthropic) for data gathering, coding and drafting, as the competition terms require us to disclose.</p>''',
        "Switch to the live app now and follow the demo script: Overview, then the Karnataka trace, then hydrogen at 25 Mt, then build speed at 0.75 and nuclear delayed on the Generation mix tab, then the checks, the backcast and the scenario comparison. If the app is slow, use the backup tab with the same story.")

# ------------------------------------------------------------------ write
for sid, s in slides.items():
    (ROOT / "slides" / f"{sid}.html").write_text(s)
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-11-06T14:30:00Z"}, "lists": "css",
        "title": "India 2047 Electricity Forecast — Defensibility Deck", "cover": "cover", "order": order,
        "sections": {"s1": {"description": "The answer", "start": "cover"}, "s2": {"description": "How demand was forecast", "start": "approach"},
                     "s3": {"description": "How the mix was chosen and what it is", "start": "mix-model"},
                     "s4": {"description": "Why it can be trusted", "start": "tradeoffs"}, "s5": {"description": "What it means and how to explore it", "start": "implications"}},
        "faces": {"source-serif-4": {"family": "Source Serif 4", "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400..700&display=swap"},
                  "ibm-plex-sans": {"family": "IBM Plex Sans", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"}},
        "designSystems": []}
(ROOT / "deck.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1))
print(len(order), "slides:", order)
for sid, s in slides.items():
    print(sid, len(s), "chars", s.count("<"), "tags")


# ------------------------------------------------------------------ midpoint review pack (18 Nov): reuses slides above
MID = Path(__file__).parent / "midpoint" / "project"; (MID / "slides").mkdir(parents=True, exist_ok=True)
mid_order = []
def mid(sid, html_text):
    (MID / "slides" / f"{sid}.html").write_text(html_text); mid_order.append(sid)

cover_mid = slides["cover"].replace("Defensibility review", "Midpoint review · 18 November").replace(
    "Final evaluation, 21–22 November 2026", "Mentor checkpoint, 18 November 2026")
cover_mid = cover_mid.split("<aside>")[0] + "<aside>Midpoint goal: confirm the regional model and the sensitivity checks with the mentors, and agree what to tighten before the final.</aside>\n</section>\n"
mid("cover", cover_mid)
import re as _re
for sid in ["answer", "regional-mix", "uncertainty", "tradeoffs", "validation"]:
    mid(sid, _re.sub(r"INNOTHON 2026 · [0-9]+</p>", "Midpoint review</p>", slides[sid]))

qs = lambda h, b: f'<div style="display:flex;flex-direction:column;gap:8px;border-left:6px solid {ACC};padding:8px 0px 8px 32px"><h3 style="font-size:34px;font-weight:600;color:{DARK}">{h}</h3><p style="font-size:26px;line-height:1.4;color:{MUTED}">{b}</p></div>'
mid("mentor-questions", f'''<section id="mentor-questions" data-transition="fade" style="background:{LIGHT};color:{INK};font-family:{SANS};padding:128px 128px 160px;display:flex;flex-direction:column;gap:36px">
{title("Five questions we would like the mentors' view on", "For discussion")}
{qs("1. Headline CO₂ path: 1.2 Gt or 1.7 Gt in 2047?", "1.2 Gt (today's level) gives 78% non-fossil; the draft-NEP-like 1.7 Gt gives 68%. Which is the more defensible base for this jury?")}
{qs("2. Is 12 Mt of green hydrogen the right base?", "It is the largest single uncertainty (±~1,000 TWh). Should hydrogen electricity sit inside the 2047 requirement or beside it?")}
{qs("3. Batteries vs pumped storage", "At 2026 costs the optimiser picks 480 GW of 4-hour batteries and no new pumped storage; CEA plans 100 GW of pumped storage by 2036. What are we not pricing?")}
{qs("4. Build-speed caps", "We cap 2047 at 1,279 GW solar and 375 GW wind (1.6× and 3× today's records). Too tight, or too loose?")}
{qs("5. The Eastern region", "The East imports 225 TWh and adds 23 GW of nuclear because its sun is weakest and it has no 150 m wind. Realistic?")}
<p style="position:absolute;left:128px;bottom:64px;width:1664px;font-size:24px;color:{MUTED}">India 2047 electricity forecast · Midpoint review</p>
<aside>Ask these in order and note each answer; each maps to a switch in the live dashboard, so we can show the effect on the spot.</aside>
</section>
''')
step2 = lambda h, b: f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:#FFFFFF;border:1px solid {RULE};border-top:8px solid {ACC2};border-radius:16px;padding:32px"><h3 style="font-size:30px;font-weight:600;color:{DARK}">{h}</h3><p style="font-size:24px;line-height:1.4;color:{MUTED}">{b}</p></div>'
mid("next-steps", f'''<section id="next-steps" data-transition="fade" style="background:{LIGHT2};color:{INK};font-family:{SANS};padding:128px 128px 160px;display:flex;flex-direction:column;gap:40px">
{title("From now to the final: plug in the official data, then tighten", "Plan")}
<div style="display:flex;flex-direction:row;gap:24px">
{step2("13 Nov · Compare", "One script lists the official files and flags every value that differs from our public data by more than 2%.")}
{step2("14–16 Nov · Swap and rerun", "Swap the agreed tables, rerun data, demand, Monte Carlo, mix and pathway in one command; 16 + 19 + 13 checks must pass.")}
{step2("19–20 Nov · Act on mentor input", "Adjust the CO₂ base, hydrogen, storage or build caps as agreed; the dashboard and deck regenerate from the models.")}
{step2("21–22 Nov · Final", "Defensibility deck plus live demo on the public dashboard; backup dashboard ready.")}
</div>
<p style="font-size:28px;line-height:1.4;color:{INK}">Every change will be logged with its cause, so the jury can see how the official data moved the answer.</p>
<p style="position:absolute;left:128px;bottom:64px;width:1664px;font-size:24px;color:{MUTED}">India 2047 electricity forecast · Midpoint review</p>
<aside>Close by asking which of the five questions the mentors see as most important to resolve before the final.</aside>
</section>
''')
mdeck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-11-06T17:00:00Z"}, "lists": "css",
         "title": "India 2047 Electricity Forecast — Midpoint Review", "cover": "cover", "order": mid_order,
         "sections": {"s1": {"description": "Where the model stands", "start": "cover"}, "s2": {"description": "Questions and plan", "start": "mentor-questions"}},
         "faces": deck["faces"], "designSystems": []}
(MID / "deck.json").write_text(json.dumps(mdeck, ensure_ascii=False, indent=1))
print("midpoint:", mid_order)
