// Final 7-slide deck for INNOTHON 2026. Numbers come from final/deck_data.json, written by final/deck_data.py from out/.
const pptxgen = require("pptxgenjs");
let applyTheme = null;
try { ({ applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js")); } catch (e) { /* optional: writes theme colours */ }
const D = require("./deck_data.json");

const THEME = {
  name: "Night Grid", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "13203A", lt1: "FFFFFF", dk2: "0D1626", lt2: "EEF2F7", accent1: "F5B83D", accent2: "3CC5A8",
            accent3: "4F9BF5", accent4: "A88BFA", accent5: "D08A4E", accent6: "8C96A6", hlink: "C98A0E", folHlink: "8C96A6" },
};
const HEX = { ink: "0D1626", text: "13203A", muted: "5B6B82", line: "D5DCE6", soft: "EEF2F7", gold: "F5B83D",
              coal: "8C96A6", gas: "D08A4E", nuclear: "A88BFA", hydro: "4F9BF5", solar: "F5B83D", wind: "3CC5A8",
              onDark: "E8EEF7", onDarkMuted: "A9B6C8" };
const SRC = ["coal", "gas", "nuclear", "hydro", "solar", "wind"];
const LAB = { coal: "Coal", gas: "Natural gas", nuclear: "Nuclear", hydro: "Hydro", solar: "Solar", wind: "Wind" };
const f0 = (v) => Math.round(v).toLocaleString("en-IN").replace(/^(\d+),(\d{3})$/, "$1,$2");
const fmt = (v) => Math.round(v).toLocaleString("en-US");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "India 2047 electricity generation forecast"; pres.author = "Manash, NIT Karnataka";
const C = pres.SchemeColor;

const FOOT = "India 2047 electricity forecast · INNOTHON 2026";
pres.defineSlideMaster({
  title: "Dark", background: { color: HEX.ink },
  objects: [{ text: { text: FOOT, options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: HEX.onDarkMuted, isTextBox: true } } }],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: HEX.onDarkMuted, align: "right" },
});
pres.defineSlideMaster({
  title: "Content", background: { color: "FFFFFF" },
  objects: [{ text: { text: FOOT, options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: HEX.muted, isTextBox: true } } }],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
});

function title(s, t, sub) {
  s.addText(t, { x: 0.6, y: 0.35, w: 12.1, h: 0.75, fontFace: "Cambria", fontSize: 28, bold: true, color: HEX.text, margin: 0, isTextBox: true, valign: "top" });
  if (sub) s.addText(sub, { x: 0.6, y: 1.1, w: 12.1, h: 0.4, fontSize: 15, color: HEX.muted, margin: 0, isTextBox: true });
}
function stat(s, x, y, w, big, small, dark) {
  s.addText(big, { x, y, w, h: 0.75, fontFace: "Cambria", fontSize: 38, bold: true, color: dark ? HEX.onDark : HEX.text, margin: 0, isTextBox: true });
  s.addText(small, { x, y: y + 0.75, w, h: 0.55, fontSize: 13, color: dark ? HEX.onDarkMuted : HEX.muted, margin: 0, isTextBox: true, valign: "top" });
}
const axis = { catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
               catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E3E8EF", size: 0.75 },
               catAxisLabelRotate: 0, catGridLine: { style: "none" }, legendFontFace: "+mn-lt", legendFontSize: 11, legendColor: HEX.muted };

// ---------------------------------------------------------------- 1 answer
{
  const s = pres.addSlide({ masterName: "Dark" });
  s.addText("ExxonMobil INNOTHON 2026 · Final evaluation · Manash, NIT Karnataka Surathkal", { x: 0.6, y: 0.45, w: 12, h: 0.35, fontSize: 13, color: HEX.gold, margin: 0, isTextBox: true });
  s.addText(`India will need about ${fmt(D.total)} TWh of electricity in 2047, and can make ${Math.round(D.nonfossil)}% of it without fossil fuels`,
    { x: 0.6, y: 1.0, w: 7.3, h: 2.6, fontFace: "Cambria", fontSize: 36, bold: true, color: HEX.onDark, margin: 0, isTextBox: true, valign: "top" });
  s.addText("A forecast built only on electricity generated, for India and its five CEA grid regions, with a least-cost regional generation plan for FY2046-47.",
    { x: 0.6, y: 3.7, w: 7.0, h: 0.9, fontSize: 16, color: HEX.onDarkMuted, margin: 0, isTextBox: true, valign: "top" });
  stat(s, 0.6, 4.85, 2.4, `${(D.total / D.fy26).toFixed(1)}×`, `FY26's ${fmt(D.fy26)} TWh; ${D.cagr.toFixed(1)}% a year`, true);
  stat(s, 3.1, 4.85, 2.8, `${fmt(D.p10)}–${fmt(D.p90)}`, "TWh, likely range (Monte Carlo P10–P90)", true);
  stat(s, 6.1, 4.85, 1.8, `₹${D.cost.toFixed(2)}`, "per kWh, all-in system cost", true);
  // mix bar on right
  s.addText("2047 generation mix", { x: 8.5, y: 1.0, w: 4.2, h: 0.35, fontSize: 14, bold: true, color: HEX.onDark, margin: 0, isTextBox: true });
  let y = 1.5;
  SRC.slice().sort((a, b) => D.mix[b] - D.mix[a]).forEach((k) => {
    s.addText(LAB[k], { x: 8.5, y, w: 1.4, h: 0.42, fontSize: 13, color: HEX.onDarkMuted, margin: 0, isTextBox: true, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.95, y: y + 0.08, w: Math.max(0.05, D.mix[k] / 45 * 2.2), h: 0.26, fill: { color: HEX[k] }, line: { type: "none" }, rectRadius: 0.05, objectName: `mix-${k}` });
    s.addText(`${D.mix[k].toFixed(1)}%`, { x: 9.95 + Math.max(0.05, D.mix[k] / 45 * 2.2) + 0.1, y, w: 0.9, h: 0.42, fontSize: 13, bold: true, color: HEX.onDark, margin: 0, isTextBox: true, valign: "middle" });
    y += 0.5;
  });
  s.addText(`Power-sector CO₂ held at ${D.co2 / 1000} Gt, today's level · ${Math.round(D.bess)} GW of batteries`, { x: 8.5, y: 4.6, w: 4.2, h: 0.6, fontSize: 13, color: HEX.onDarkMuted, margin: 0, isTextBox: true, valign: "top" });
  s.addText([
    { text: "Live dashboard: ", options: { color: HEX.onDarkMuted } },
    { text: D.app_short, options: { color: HEX.gold, hyperlink: { url: D.app } , breakLine: true } },
    { text: "Code and data: ", options: { color: HEX.onDarkMuted } },
    { text: D.repo_short, options: { color: HEX.gold, hyperlink: { url: D.repo } } },
  ], { x: 8.5, y: 5.35, w: 4.4, h: 0.9, fontSize: 12, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 4 });
  s.addNotes(`Open with the answer: about ${fmt(D.total)} terawatt-hours generated in FY2046-47, ${(D.total / D.fy26).toFixed(1)} times today, and ${Math.round(D.nonfossil)} percent of it non-fossil while power emissions stay at today's 1.2 gigatonnes, at ${D.cost.toFixed(2)} rupees a unit. Every number is fitted and compared on energy generated, as the problem statement requires. The next six slides show how we got there and why it holds up.`);
}

// ---------------------------------------------------------------- 2 method
{
  const s = pres.addSlide({ masterName: "Content" });
  title(s, "Two linked models turn official generation data into a plan", "Every forecast and every comparison uses electricity generated. Installed capacity and consumption are never used as a basis.");
  const steps = [
    ["Data", "Official INNOTHON dataset (state population, GSDP); NPP/CEA region-wise generation FY19–26; Grid-India inter-regional flows; MoP national generation FY10–26; UN WPP 2024"],
    ["Demand", `Generation per person grows with GDP per person: elasticity ${D.b.toFixed(2)} (SE ${D.b_se.toFixed(2)}), fitted on national generation; each region from its own GSDP and population`],
    ["New loads", `EVs, data centres and green hydrogen (${D.h2_mt} Mt) added bottom-up, because history cannot contain them`],
    ["Cross-checks", `Back-test, ARIMA / ETS / ARIMAX time-series models, 2,000-run Monte Carlo, tornado sensitivity`],
    ["Regional mix", "Least-cost optimiser: 5 regions × 6 sources × 12 time slices, with resource limits, build speed, grid corridors, storage and a CO₂ cap"],
  ];
  const w = 2.3, gap = 0.15;
  steps.forEach(([h, t], i) => {
    const x = 0.6 + i * (w + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.75, w, h: 3.55, fill: { color: HEX.soft }, line: { type: "none" }, rectRadius: 0.12, objectName: `step-${i}` });
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.95, w: 0.5, h: 0.5, fill: { color: [HEX.hydro, HEX.wind, HEX.nuclear, HEX.gas, HEX.solar][i] }, line: { type: "none" }, objectName: `stepdot-${i}` });
    s.addText(String(i + 1), { x: x + 0.25, y: 1.95, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(h, { x: x + 0.2, y: 2.55, w: w - 0.4, h: 0.45, fontSize: 18, bold: true, color: HEX.text, margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.2, y: 3.0, w: w - 0.35, h: 2.25, fontSize: 13, color: HEX.muted, margin: 0, isTextBox: true, valign: "top" });
  });
  s.addText([
    { text: "Why generation only works here: ", options: { bold: true, color: HEX.text } },
    { text: `a region's need = what it generates + what it imports from other regions. Regional generation plus Bhutan imports matches national generation to 0.0% in every year FY19–26, so the regional split is consistent by construction. Capacity enters the optimiser only as a physical limit, never as a forecast or a benchmark.`, options: { color: HEX.muted } },
  ], { x: 0.6, y: 5.55, w: 12.1, h: 1.2, fontSize: 14, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("The method in one picture. Data, then a demand model fitted on generation, then new loads that history cannot show, then cross-checks, then a least-cost optimiser that decides how each region generates its share. The key compliance point: a region's requirement is its own generation plus net imports, both measured quantities of energy generated or moved, so no consumption data is needed anywhere.");
}

// ---------------------------------------------------------------- 3 demand forecast + time series
{
  const s = pres.addSlide({ masterName: "Content" });
  title(s, `Generation rises ${(D.total / D.fy26).toFixed(1)}× by 2047; time-series models confirm the trend`, "TWh generated per year. History from MoP/CEA; forecast from the generation-based model.");
  const yrs = D.years, labels = yrs.map((y) => (y % 5 === 0 || y === 2047 || y === 2026 ? `FY${String(y).slice(2)}` : ""));
  s.addChart(pres.charts.LINE, [
    { name: "Actual", labels, values: yrs.map((y) => D.hist[y] ?? null) },
    { name: "Forecast incl. green H₂", labels, values: yrs.map((y) => (y >= 2026 ? D.fc_total[y] : null)) },
    { name: "Forecast, grid only", labels, values: yrs.map((y) => (y >= 2026 ? D.fc_grid[y] : null)) },
    { name: "ARIMA trend", labels, values: yrs.map((y) => (y >= 2027 ? D.ts.arima[y] : null)) },
  ], { x: 0.5, y: 1.6, w: 7.6, h: 5.2, ...axis, chartColors: [HEX.text, HEX.gold, "E07A5F", HEX.hydro], lineSize: 2.5, lineDataSymbol: "none",
       showLegend: true, legendPos: "b", valAxisLabelFormatCode: "#,##0", valAxisMinVal: 0, objectName: "chart-forecast" });
  const rows = [
    [{ text: "Model (2047)", options: { bold: true, color: HEX.muted } }, { text: "TWh", options: { bold: true, color: HEX.muted, align: "right" } }, { text: "Back-test error", options: { bold: true, color: HEX.muted, align: "right" } }],
    [{ text: "Our model, total", options: { bold: true } }, { text: fmt(D.total), options: { align: "right", bold: true } }, { text: `${D.bt_struct.toFixed(1)}%`, options: { align: "right", bold: true } }],
    ["Our model, grid only (no H₂)", { text: fmt(D.fc_grid[2047]), options: { align: "right" } }, { text: "–", options: { align: "right" } }],
    ["ARIMAX (GDP-driven)", { text: fmt(D.ts_sum.ARIMAX.v), options: { align: "right" } }, { text: `${D.ts_sum.ARIMAX.e.toFixed(1)}%`, options: { align: "right" } }],
    ["ARIMA trend", { text: fmt(D.ts_sum.ARIMA.v), options: { align: "right" } }, { text: `${D.ts_sum.ARIMA.e.toFixed(1)}%`, options: { align: "right" } }],
    ["ETS damped trend (floor)", { text: fmt(D.ts_sum.ETS.v), options: { align: "right" } }, { text: `${D.ts_sum.ETS.e.toFixed(1)}%`, options: { align: "right" } }],
  ];
  s.addTable(rows, { x: 8.45, y: 1.7, w: 4.3, colW: [2.3, 0.9, 1.1], fontSize: 13, color: HEX.text, border: { type: "solid", pt: 0.5, color: HEX.line }, rowH: 0.38, margin: 0.05, objectName: "ts-table" });
  s.addText([
    { text: "How to read it: ", options: { bold: true, color: HEX.text } },
    { text: `models that only extrapolate history land at ${fmt(D.ts_sum.ARIMAX.v)}–${fmt(D.ts_sum.ARIMA.v)} TWh, beside our grid-only ${fmt(D.fc_grid[2047])}. The gap to ${fmt(D.total)} is green hydrogen (${fmt(D.h2)} TWh) and faster EV and data-centre growth, which no past series contains.`, options: { color: HEX.muted, breakLine: true } },
    { text: "Back-test: ", options: { bold: true, color: HEX.text } },
    { text: `fitted only to FY19, our model predicts FY24–26 with ${D.bt_struct.toFixed(1)}% mean error, the best of all models tested.`, options: { color: HEX.muted } },
  ], { x: 8.45, y: 4.2, w: 4.3, h: 2.5, fontSize: 13, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 6 });
  s.addNotes(`Demand is fitted directly on generation: a 1% rise in GDP per person raises generation per person by about ${D.b.toFixed(2)}%, easing as the economy matures. We checked it three ways. Back-test: fitted only to 2019, it predicted 2024 and 2025 within about one percent. Time-series models with no economics in them, ARIMA and ARIMAX, land at about 5,400 to 5,500 terawatt-hours, right beside our grid-only figure. The difference to 6,030 is green hydrogen and the newer loads that history cannot contain. The damped exponential-smoothing model assumes growth dies out, so we treat it as a floor.`);
}

// ---------------------------------------------------------------- 4 regional
{
  const s = pres.addSlide({ masterName: "Content" });
  title(s, "Each region generates from what its land offers", "2047 generation by source and region, TWh, base plan (1.2 Gt CO₂ cap). The East imports clean power over expanded corridors.");
  const regs = D.regions;
  s.addChart(pres.charts.BAR, SRC.map((k) => ({ name: LAB[k], labels: regs.map((r) => r.name), values: regs.map((r) => r.gen[k]) })),
    { x: 0.5, y: 1.6, w: 6.4, h: 5.1, barDir: "bar", barGrouping: "stacked", ...axis, chartColors: SRC.map((k) => HEX[k]),
      showLegend: true, legendPos: "b", valAxisLabelFormatCode: "#,##0", catAxisOrientation: "maxMin", objectName: "chart-regions" });
  const head = ["Region", "Need 2047", "Generates", "Role in the plan"].map((t, i) => ({ text: t, options: { bold: true, color: HEX.muted, align: i && i < 3 ? "right" : "left" } }));
  const rows = [head].concat(regs.map((r) => [
    { text: r.name, options: { bold: true } }, { text: fmt(r.need), options: { align: "right" } }, { text: fmt(r.total), options: { align: "right" } }, r.role,
  ]));
  s.addTable(rows, { x: 7.2, y: 1.7, w: 5.6, colW: [1.35, 0.95, 1.0, 2.3], fontSize: 12, color: HEX.text, border: { type: "solid", pt: 0.5, color: HEX.line }, margin: 0.05, valign: "middle", objectName: "region-table" });
  s.addText(`Regional need = own generation + net imports in FY24–26, grown with each region's own GSDP and population. The South grows fastest (${D.south_x.toFixed(1)}×) on data centres and hydrogen.`,
    { x: 7.2, y: 4.85, w: 5.6, h: 0.9, fontSize: 13, color: HEX.muted, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("This is the regional strategy. The North is the solar hub and exports midday power. The West balances solar, wind and cheap pithead coal. The South pairs its strong wind with nuclear because its sun is weaker. The East has the weakest sun and no wind at 150 metres, so it keeps pithead coal, adds nuclear, and imports clean power over expanded corridors. The North-East is hydro and exports. The live dashboard shows this on a 3D map with the power flows drawn as arcs.");
}

// ---------------------------------------------------------------- 5 national mix + pathway
{
  const s = pres.addSlide({ masterName: "Content" });
  title(s, "Clean power carries all the growth; coal stays near today's level", "Generation by source at each milestone, TWh, least-cost plan solved year by year.");
  const P = D.pathway;
  s.addChart(pres.charts.BAR, SRC.map((k) => ({ name: LAB[k], labels: P.map((p) => p.label), values: P.map((p) => p[k]) })),
    { x: 0.5, y: 1.6, w: 7.4, h: 5.1, barDir: "col", barGrouping: "stacked", ...axis, chartColors: SRC.map((k) => HEX[k]),
      showLegend: true, legendPos: "b", valAxisLabelFormatCode: "#,##0", objectName: "chart-pathway" });
  const st = [
    [`${Math.round(D.nonfossil)}%`, `non-fossil in 2047, from ${Math.round(P[0].nf)}% in FY26`],
    [`${fmt(D.solar_gw)} GW`, `solar by 2047, about 82 GW a year after 2036; ${fmt(D.wind_gw)} GW wind`],
    [`${fmt(D.nuc_gw)} GW`, "nuclear, the clean firm power that lets coal plateau"],
    [`${fmt(D.bess)} GW`, "4-hour batteries move midday sun into the evening peak"],
  ];
  st.forEach(([b, t], i) => stat(s, 8.4, 1.65 + i * 1.3, 4.4, b, t, false));
  s.addNotes(`The same optimiser solved for FY30, FY35, FY40 and FY47 with that year's demand, committed fleet and build limits. FY30 lands near CEA's National Electricity Plan, at about ${Math.round(P[1].coal_pct)} percent coal and ${(P[1].co2 / 1000).toFixed(2)} gigatonnes. No new coal is built beyond what is committed; the fleet runs mainly at night and in the low-wind winter. Solar is built as fast as India can build it.`);
}

// ---------------------------------------------------------------- 6 uncertainty and trade-offs
{
  const s = pres.addSlide({ masterName: "Content" });
  title(s, "How fast India builds matters more than what technology costs", "Left: change in 2047 generation, one driver at a time (TWh). Right: the 2047 plan under alternative policies.");
  const T = D.tornado;
  s.addChart(pres.charts.BAR, [
    { name: "Low case", labels: T.map((t) => t.label), values: T.map((t) => t.low) },
    { name: "High case", labels: T.map((t) => t.label), values: T.map((t) => t.high) },
  ], { x: 0.5, y: 1.6, w: 5.9, h: 5.1, barDir: "bar", barGrouping: "stacked", ...axis, chartColors: ["9AA6B8", HEX.wind], overlap: 100,
       showLegend: true, legendPos: "b", valAxisLabelFormatCode: "#,##0", catAxisLabelFontSize: 10, catAxisLabelPos: "low", objectName: "chart-tornado" });
  const head = ["2047 scenario", "Non-fossil", "CO₂ Mt", "₹/kWh"].map((t, i) => ({ text: t, options: { bold: true, color: HEX.muted, align: i ? "right" : "left" } }));
  const rows = [head].concat(D.scen.map((r, i) => [
    { text: r.name, options: { bold: i === 0 } }, { text: `${r.nf.toFixed(1)}%`, options: { align: "right", bold: i === 0 } },
    { text: r.over > 0.5 ? `${fmt(r.co2)} (+${fmt(r.over)})` : fmt(r.co2), options: { align: "right", bold: i === 0, color: r.over > 0.5 ? "B4462F" : HEX.text } },
    { text: r.cost.toFixed(2), options: { align: "right", bold: i === 0 } },
  ]));
  s.addTable(rows, { x: 6.75, y: 1.7, w: 6.05, colW: [2.75, 1.0, 1.4, 0.9], fontSize: 12.5, color: HEX.text, border: { type: "solid", pt: 0.5, color: HEX.line }, rowH: 0.36, margin: 0.05, objectName: "scen-table" });
  s.addText(`Building solar and wind 25% slower overshoots the CO₂ cap by ${fmt(D.slow_over)} Mt; delaying nuclear overshoots it by ${fmt(D.nuc_over)} Mt and brings back imported gas. Solar 30% dearer raises the price but leaves the mix unchanged: solar is already limited by build speed, not cost.`,
    { x: 6.75, y: 5.0, w: 6.05, h: 1.4, fontSize: 13, color: HEX.muted, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes(`GDP, hydrogen policy and the income response each move 2047 by about a thousand terawatt-hours; population and delivery losses barely matter. All drivers together give a P10 to P90 band of ${fmt(D.p10)} to ${fmt(D.p90)}. On the supply side, the binding constraint is delivery: permitting, land, manufacturing and transmission. A slower build or a delayed nuclear programme pushes India back to coal and imported gas.`);
}

// ---------------------------------------------------------------- 7 proof + implications + links
{
  const s = pres.addSlide({ masterName: "Dark" });
  s.addText("Tested on today's grid, then turned into four actions", { x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontFace: "Cambria", fontSize: 30, bold: true, color: HEX.onDark, margin: 0, isTextBox: true });
  const proofs = [
    [`${D.bt_struct.toFixed(1)}%`, "mean error predicting FY24–26 generation from data up to FY19"],
    [`±${D.backcast_err.toFixed(1)} pts`, "largest error when the optimiser reproduces the actual FY26 generation mix from today's fleet"],
    ["0.0%", "gap between regional generation (NPP/CEA) and national generation (MoP), every year FY19–26"],
    [`${Math.round(D.fy30_coal)}% · ${(D.fy30_co2 / 1000).toFixed(2)} Gt`, "FY30 coal share and CO₂, beside CEA NEP's ~50% and 1.18 Gt for FY32"],
  ];
  proofs.forEach(([b, t], i) => {
    const x = 0.6 + i * 3.08;
    s.addText(b, { x, y: 1.45, w: 2.9, h: 0.65, fontFace: "Cambria", fontSize: 28, bold: true, color: HEX.gold, margin: 0, isTextBox: true });
    s.addText(t, { x, y: 2.1, w: 2.85, h: 0.95, fontSize: 13, color: HEX.onDarkMuted, margin: 0, isTextBox: true, valign: "top" });
  });
  const acts = [
    ["Build ~82 GW of solar a year", "and ~23 GW of wind from the mid-2030s: about 1.8× and 3.8× today's records."],
    ["Wire the East", "triple inter-regional corridors so northern and western solar can reach it."],
    ["Keep nuclear on schedule", "100 GW of clean firm power lets coal plateau; delay brings back gas."],
    ["Store the sun", `about ${Math.round(D.bess / 10) * 10} GW of batteries, mostly beside solar plants.`],
  ];
  acts.forEach(([h, t], i) => {
    const x = 0.6 + i * 3.08;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.35, w: 2.9, h: 2.0, fill: { color: "17284A" }, line: { type: "none" }, rectRadius: 0.12, objectName: `act-${i}` });
    s.addText(h, { x: x + 0.2, y: 3.5, w: 2.5, h: 0.7, fontSize: 16, bold: true, color: HEX.onDark, margin: 0, isTextBox: true, valign: "top" });
    s.addText(t, { x: x + 0.2, y: 4.2, w: 2.5, h: 1.05, fontSize: 13, color: HEX.onDarkMuted, margin: 0, isTextBox: true, valign: "top" });
  });
  s.addText([
    { text: "Live dashboard (models re-run on every slider): ", options: { color: HEX.onDarkMuted } },
    { text: D.app, options: { color: HEX.gold, hyperlink: { url: D.app }, breakLine: true } },
    { text: "GitHub (data, models, tests; one command rebuilds everything): ", options: { color: HEX.onDarkMuted } },
    { text: D.repo, options: { color: HEX.gold, hyperlink: { url: D.repo }, breakLine: true } },
    { text: "AI use: built with help from Claude (Anthropic) for data gathering, coding and drafting, as the competition terms require us to disclose.", options: { color: HEX.onDarkMuted } },
  ], { x: 0.6, y: 5.6, w: 12.1, h: 1.25, fontSize: 12, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 3 });
  s.addNotes("Close on proof and action. The demand model predicted the recent past, the optimiser reproduced today's grid, the regional data reconciles exactly with the national total, and our 2030 point sits beside the national plan. The four actions follow directly from the constraints that bind in the model. Then switch to the live dashboard for the demo.");
}

(async () => {
  await pres.writeFile({ fileName: "India_2047_Electricity_INNOTHON_Final.pptx" });
  if (applyTheme) await applyTheme("India_2047_Electricity_INNOTHON_Final.pptx", THEME);
  console.log("written");
})();
