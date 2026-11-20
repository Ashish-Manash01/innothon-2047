// Final 7-slide deck, INNOTHON 2026. Ashish Manash, Team Innovexa.
// Numbers come from final/deck_data.json (written by final/deck_data.py from out/), so the deck always matches the models.
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fa = require("react-icons/fa");
let applyTheme = null;
try { ({ applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js")); } catch (e) { /* optional */ }
const D = require("./deck_data.json");

const THEME = {
  name: "Innovexa", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "13203A", lt1: "FFFFFF", dk2: "0D1626", lt2: "F3F5F8", accent1: "F2B134", accent2: "3CB49A",
            accent3: "4F8FE0", accent4: "A88BFA", accent5: "E07A5F", accent6: "8C96A6", hlink: "B7790A", folHlink: "8C96A6" },
};
const K = { navy: "0D1626", ink: "13203A", muted: "5B6B82", soft: "F3F5F8", line: "DCE2EA", gold: "F2B134",
            coal: "8C96A6", gas: "D08A4E", nuclear: "A88BFA", hydro: "4F8FE0", solar: "F2B134", wind: "3CB49A",
            onDark: "F4F6FA", onDarkMuted: "AEB9CA" };
const RC = { Northern: "F2B134", Western: "E07A5F", Southern: "3CB49A", Eastern: "8C96A6", "North-Eastern": "4F8FE0" };
const fmt = (v) => Math.round(v).toLocaleString("en-US");

async function icon(Comp, color, px = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "How much electricity will India need in 2047?";
  pres.author = "Ashish Manash, Team Innovexa";
  pres.company = "Team Innovexa";

  const FOOT = "Ashish Manash, Team Innovexa  |  INNOTHON 2026";
  pres.defineSlideMaster({ title: "Dark", background: { color: K.navy },
    slideNumber: { x: 12.3, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: K.onDarkMuted, align: "right" } });
  pres.defineSlideMaster({ title: "Light", background: { color: "FFFFFF" },
    objects: [{ text: { text: FOOT, options: { x: 0.7, y: 6.95, w: 8, h: 0.3, fontSize: 10, color: K.muted, isTextBox: true } } }],
    slideNumber: { x: 12.3, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: K.muted, align: "right" } });

  const title = (s, t) => s.addText(t, { x: 0.7, y: 0.45, w: 11.9, h: 0.85, fontSize: 34, bold: true, color: K.ink, margin: 0, isTextBox: true, valign: "top" });
  const say = (s, t, o) => s.addText(t, { fontSize: 16, color: K.muted, margin: 0, isTextBox: true, valign: "top", ...o });

  // ================================================================ 1 cover
  {
    const s = pres.addSlide({ masterName: "Dark" });
    s.addImage({ path: "india_cover.png", x: 7.55, y: 0.45, w: 5.2, h: 5.65, transparency: 15, altText: "Map of India coloured by its five electricity grid regions" });
    s.addText("ExxonMobil INNOTHON 2026", { x: 0.8, y: 0.8, w: 6, h: 0.4, fontSize: 16, color: K.gold, bold: true, margin: 0, isTextBox: true });
    s.addText("How much electricity will India need in 2047, and where should it come from?",
      { x: 0.8, y: 1.45, w: 6.6, h: 2.8, fontSize: 40, bold: true, color: K.onDark, margin: 0, isTextBox: true, valign: "top" });
    s.addText([
      { text: "Ashish Manash", options: { fontSize: 22, bold: true, color: K.onDark, breakLine: true } },
      { text: "Team Innovexa", options: { fontSize: 18, color: K.gold, breakLine: true } },
      { text: "NIT Karnataka, Surathkal", options: { fontSize: 15, color: K.onDarkMuted } },
    ], { x: 0.8, y: 4.75, w: 6, h: 1.4, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 2 });
    s.addNotes("Hello, I'm Ashish Manash from Team Innovexa. Our question is simple: how much electricity will India have to generate in 2047, and what should each part of the country generate it from? In the next six slides I'll give you the answer first, then show how I got there and why I trust it.");
  }

  // ================================================================ 2 the answer
  {
    const s = pres.addSlide({ masterName: "Light" });
    title(s, "Our answer in three numbers");
    const cols = [
      [`${fmt(D.total)}`, "TWh", `electricity India will generate in 2047. That's ${(D.total / D.fy26).toFixed(1)} times what it generated last year.`],
      [`${Math.round(D.nonfossil)}%`, "clean", "of it from solar, wind, nuclear and hydro, while power-sector emissions stay at today's level."],
      [`₹${D.cost.toFixed(2)}`, "per unit", "average cost of electricity, covering plants, batteries and transmission. Cheaper than new coal."],
    ];
    cols.forEach(([big, unit, line], i) => {
      const x = 0.7 + i * 4.1;
      s.addText([{ text: big, options: { fontSize: 60, bold: true, color: K.ink } }, { text: "  " + unit, options: { fontSize: 22, color: K.gold, bold: true } }],
        { x, y: 1.65, w: 3.9, h: 1.1, margin: 0, isTextBox: true, valign: "bottom" });
      say(s, line, { x, y: 2.85, w: 3.6, h: 1.1 });
    });
    s.addText("Where the 2047 electricity comes from", { x: 0.7, y: 4.35, w: 8, h: 0.4, fontSize: 18, bold: true, color: K.ink, margin: 0, isTextBox: true });
    const order = ["solar", "wind", "nuclear", "hydro", "coal", "gas"];
    const LAB = { solar: "Solar", wind: "Wind", nuclear: "Nuclear", hydro: "Hydro", coal: "Coal", gas: "Gas" };
    let x = 0.7; const W = 11.9;
    order.forEach((k) => {
      const w = W * D.mix[k] / 100;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 4.9, w, h: 0.55, fill: { color: K[k] }, line: { color: "FFFFFF", width: 1.5 }, objectName: `mix-${k}` });
      if (D.mix[k] > 4) s.addText([{ text: LAB[k], options: { bold: true, breakLine: true } }, { text: `${Math.round(D.mix[k])}%` }],
        { x, y: 5.55, w: Math.max(w, 1), h: 0.65, fontSize: 14, color: K.ink, margin: 0, isTextBox: true, valign: "top" });
      x += w;
    });
    say(s, `Gas ${D.mix.gas.toFixed(0)}%, kept as backup. Likely range for the total: ${fmt(Math.round(D.p10 / 50) * 50)} to ${fmt(Math.round(D.p90 / 50) * 50)} TWh.`,
      { x: 7.3, y: 6.25, w: 5.3, h: 0.4, fontSize: 13, align: "right" });
    s.addNotes(`Three numbers. First, India will need to generate about ${fmt(D.total)} terawatt-hours in 2047, roughly three times today. Second, ${Math.round(D.nonfossil)} percent of that can come from clean sources while keeping power-sector emissions flat at about 1.2 billion tonnes. Third, it stays affordable, about ${D.cost.toFixed(2)} rupees a unit. Solar alone becomes India's biggest source; coal drops to about a fifth.`);
  }

  // ================================================================ 3 how
  {
    const s = pres.addSlide({ masterName: "Light" });
    title(s, "How I worked it out");
    const steps = [
      [Fa.FaHistory, K.hydro, "Learn from the past", "17 years of India's electricity generation, GDP and population, plus the official INNOTHON dataset and grid data for each region."],
      [Fa.FaChartLine, K.gold, "Project the future", `When income per person rises 1%, generation per person rises about ${D.b.toFixed(2)}%. I add what the past can't show: EVs, data centres and green hydrogen.`],
      [Fa.FaSolarPanel, K.wind, "Plan the supply", "An optimiser picks the cheapest mix for each of India's five grid regions, within real limits on land, build speed, transmission and CO₂."],
    ];
    for (let i = 0; i < 3; i++) {
      const [Ic, c, h, t] = steps[i]; const x = 0.7 + i * 4.15;
      s.addShape(pres.shapes.OVAL, { x, y: 1.75, w: 1.0, h: 1.0, fill: { color: K.soft }, line: { type: "none" }, objectName: `step-ring-${i}` });
      s.addImage({ data: await icon(Ic, c), x: x + 0.25, y: 2.0, w: 0.5, h: 0.5, altText: h });
      s.addText(h, { x, y: 3.0, w: 3.6, h: 0.5, fontSize: 22, bold: true, color: K.ink, margin: 0, isTextBox: true });
      say(s, t, { x, y: 3.55, w: 3.55, h: 1.6 });
      if (i < 2) s.addImage({ data: await icon(Fa.FaArrowRight, "C3CBD6"), x: x + 3.7, y: 2.05, w: 0.4, h: 0.4, altText: "then" });
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.7, y: 5.45, w: 11.9, h: 0.95, fill: { color: K.soft }, line: { type: "none" }, rectRadius: 0.1, objectName: "rule-box" });
    s.addText([
      { text: "Following the rules: ", options: { bold: true, color: K.ink } },
      { text: "every forecast and comparison uses electricity generated, never consumption or installed capacity. A region's need is what it generates plus what it imports from other regions.", options: { color: K.muted } },
    ], { x: 1.0, y: 5.55, w: 11.3, h: 0.75, fontSize: 15, margin: 0, isTextBox: true, valign: "middle" });
    s.addNotes("Three steps. First I learned from the past: how India's generation has grown with its economy and population. Second I projected that forward to 2047 and added new demand that history can't show, like electric vehicles, data centres and green hydrogen. Third, an optimiser works out the cheapest way for each region to generate its share. And everything is based on electricity generated, exactly as the rules ask.");
  }

  // ================================================================ 4 trust
  {
    const s = pres.addSlide({ masterName: "Light" });
    title(s, "Why I trust the forecast");
    const yrs = D.years, labels = yrs.map((y) => (y % 5 === 0 || y === 2047 ? String(y) : ""));
    s.addChart(pres.charts.LINE, [
      { name: "Actual", labels, values: yrs.map((y) => D.hist[y] ?? null) },
      { name: "Our forecast", labels, values: yrs.map((y) => (y >= 2026 ? D.fc_total[y] : null)) },
    ], { x: 0.5, y: 1.45, w: 6.6, h: 4.9, chartColors: [K.ink, K.gold], lineSize: 3, lineDataSymbol: "none",
         catAxisLabelColor: K.muted, valAxisLabelColor: K.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelRotate: 0,
         catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E6EAF0", size: 0.75 }, catGridLine: { style: "none" },
         showLegend: true, legendPos: "t", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: K.muted,
         valAxisLabelFormatCode: "#,##0", valAxisMinVal: 0, showValAxisTitle: true, valAxisTitle: "TWh generated per year",
         valAxisTitleFontSize: 12, valAxisTitleColor: K.muted, valAxisTitleFontFace: "+mn-lt", objectName: "chart-forecast" });
    s.addText("The test", { x: 7.6, y: 1.5, w: 5, h: 0.45, fontSize: 20, bold: true, color: K.ink, margin: 0, isTextBox: true });
    say(s, "I hid 2020–2026 from every model, then asked each to predict 2024–2026. Average error, lower is better:", { x: 7.6, y: 1.95, w: 5.0, h: 0.8, fontSize: 15 });
    const bars = [["Our model", D.bt_struct, K.gold], ["ARIMAX (time series)", D.ts_sum.ARIMAX.e, "B8C1CD"], ["Neural network", D.ml["Neural network (MLP)"].e, "B8C1CD"],
                  ["Random forest", D.ml["Random forest"].e, "B8C1CD"], ["ARIMA (time series)", D.ts_sum.ARIMA.e, "B8C1CD"], ["Gradient boosting", D.ml["Gradient boosting"].e, "B8C1CD"]];
    bars.forEach(([n, e, c], i) => {
      const y = 2.9 + i * 0.5;
      s.addText(n, { x: 7.6, y, w: 2.2, h: 0.4, fontSize: 14, color: i === 0 ? K.ink : K.muted, bold: i === 0, margin: 0, isTextBox: true, valign: "middle" });
      s.addShape(pres.shapes.RECTANGLE, { x: 9.85, y: y + 0.07, w: e / 13 * 2.3, h: 0.26, fill: { color: c }, line: { type: "none" }, objectName: `err-${i}` });
      s.addText(`${e.toFixed(1)}%`, { x: 9.95 + e / 13 * 2.3, y, w: 0.8, h: 0.4, fontSize: 14, bold: i === 0, color: K.ink, margin: 0, isTextBox: true, valign: "middle" });
    });
    say(s, "Machine learning needs far more than 17 years of data, so I use it to check the forecast, not to make it.", { x: 7.6, y: 6.0, w: 5.0, h: 0.6, fontSize: 13 });
    s.addNotes(`Can you trust a forecast 21 years out? I tested it the honest way. I hid the years 2020 to 2026, trained on the rest, and asked every model to predict 2024 to 2026. Our model missed by ${D.bt_struct.toFixed(1)} percent on average, the best of everything I tried, including ARIMA time-series models, a neural network, a random forest and gradient boosting. With only 17 years of data, machine-learning models swing wildly, so I use them as a check, not as the forecaster.`);
  }

  // ================================================================ 5 regions
  {
    const s = pres.addSlide({ masterName: "Light" });
    title(s, "Every region plays to its strengths");
    s.addImage({ path: "india_regions_2047.png", x: 0.55, y: 1.3, w: 5.0, h: 5.43, altText: "Map of India's five grid regions with each region's 2047 generation in TWh" });
    const R = Object.fromEntries(D.regions.map((r) => [r.name, r]));
    const lines = [
      ["Western", "The biggest producer: Gujarat's sun and wind, plus central India's coal. Sends power to others."],
      ["Northern", "Rajasthan's deserts become India's solar hub, backed by Himalayan hydro."],
      ["Southern", "Strong winds in Tamil Nadu and Karnataka, with nuclear for when the sun is weaker."],
      ["Eastern", "Least sun and almost no wind, so it keeps its coal, adds nuclear and buys clean power from neighbours."],
      ["North-Eastern", "Hydro from Arunachal's rivers, much of it sent to the rest of India."],
    ];
    lines.forEach(([r, t], i) => {
      const y = 1.45 + i * 1.02; const net = R[r].total - R[r].need;
      s.addShape(pres.shapes.OVAL, { x: 6.1, y: y + 0.08, w: 0.28, h: 0.28, fill: { color: RC[r] }, line: { type: "none" }, objectName: `dot-${i}` });
      s.addText([{ text: r, options: { bold: true, color: K.ink } },
                 { text: `   ${net >= 0 ? "sends out" : "brings in"} ${fmt(Math.abs(net))} TWh`, options: { color: net >= 0 ? "2E8F78" : "B4562F", fontSize: 13 } }],
        { x: 6.55, y, w: 6.1, h: 0.42, fontSize: 18, margin: 0, isTextBox: true, valign: "middle" });
      say(s, t, { x: 6.55, y: y + 0.42, w: 6.1, h: 0.55, fontSize: 14 });
    });
    s.addNotes("Here's where the electricity is made in 2047; the numbers on the map are terawatt-hours. The plan isn't one mix copied everywhere. The North becomes the solar hub. The West has the most of everything and exports. The South uses its wind and adds nuclear. The East has the weakest sun and almost no wind, so it relies on coal and nuclear and imports clean power over bigger transmission lines. The North-East is hydro. The live dashboard shows this in 3D with the power flows drawn as arcs.");
  }

  // ================================================================ 6 the whole process, data to dashboard
  {
    const s = pres.addSlide({ masterName: "Light" });
    title(s, "From raw data to a live dashboard");
    const IN = "EAF2FD", PR = K.soft, OUT = "FDF3DC", AR = "9AA6B8";
    const box = (x, y, w, h, fill, head, body, name) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { type: "none" }, rectRadius: 0.1, objectName: name });
      s.addText([{ text: head, options: { bold: true, color: K.ink, fontSize: 14, breakLine: !!body } },
                 ...(body ? [{ text: body, options: { color: K.muted, fontSize: 11.5 } }] : [])],
        { x: x + 0.12, y: y + 0.06, w: w - 0.24, h: h - 0.12, margin: 0, isTextBox: true, valign: "middle", paraSpaceAfter: 2 });
    };
    const arrow = (x, y, w, h, name) => s.addShape(pres.shapes.LINE, { x, y, w, h, line: { color: AR, width: 2, endArrowType: "triangle" }, objectName: name });
    const label = (t, x) => s.addText(t, { x, y: 1.3, w: 2.4, h: 0.3, fontSize: 12, bold: true, color: K.gold, margin: 0, isTextBox: true });

    // column labels
    label("1  Data", 0.6); label("2  Check", 3.2); label("3  Forecast", 5.55); label("4  Plan", 8.0); label("5  Share", 10.5);

    // 1 data sources
    const src = [["Official INNOTHON dataset", "State population and GSDP"], ["NPP / CEA reports", "Generation by region, FY19–26"],
                 ["Grid-India", "Power traded between regions"], ["MoP, UN, MoSPI", "National generation, population, GDP"]];
    src.forEach(([h, b], i) => box(0.6, 1.7 + i * 1.12, 2.3, 0.95, IN, h, b, `src-${i}`));
    // bracket arrows into Check
    src.forEach((_, i) => s.addShape(pres.shapes.LINE, { x: 2.9, y: 2.17 + i * 1.12, w: 0.1, h: 0, line: { color: AR, width: 2 }, objectName: `a-src-${i}` }));
    s.addShape(pres.shapes.LINE, { x: 3.0, y: 2.17, w: 0, h: 3.36, line: { color: AR, width: 2 }, objectName: "bracket" });
    arrow(3.0, 3.85, 0.2, 0, "a-into-check");

    // 2 clean and check
    box(3.2, 3.15, 2.0, 1.4, PR, "Clean and check", "16 automated checks. Regions add up to the national total exactly.", "check");
    arrow(5.2, 3.85, 0.35, 0, "a-check-demand");

    // 3 forecast
    box(5.55, 3.0, 2.15, 1.7, PR, "Demand model", "Generation grows with income and population, region by region. Plus EVs, data centres, hydrogen.", "demand");
    box(5.55, 1.65, 2.15, 1.0, PR, "Validation", "Back-test, ARIMA, ETS, ARIMAX, neural network, random forest", "validate");
    box(5.55, 5.05, 2.15, 1.0, PR, "Uncertainty", "2,000 Monte Carlo runs, tornado chart", "uncert");
    arrow(6.62, 3.0, 0, -0.35, "a-demand-val"); arrow(6.62, 4.7, 0, 0.35, "a-demand-unc");
    arrow(7.7, 3.85, 0.3, 0, "a-demand-mix");

    // 4 plan
    box(8.0, 3.0, 2.15, 1.7, PR, "Mix optimiser", "Cheapest plan for 5 regions × 6 sources, day, evening and night, within limits on land, build speed, grid and CO₂.", "mix");
    box(8.0, 5.05, 2.15, 1.0, PR, "Pathway", "Same optimiser for 2030, 2035, 2040, 2047", "path");
    arrow(9.07, 4.7, 0, 0.35, "a-mix-path");
    arrow(10.15, 3.85, 0.35, 0, "a-mix-out");

    // 5 outputs
    box(10.5, 1.65, 2.2, 1.35, OUT, `${fmt(D.total)} TWh, ${Math.round(D.nonfossil)}% clean`, "National and regional answer", "out-answer");
    box(10.5, 3.2, 2.2, 1.35, OUT, "Live dashboard", "Move any slider and every model re-runs, with a 3D map", "out-dash");
    box(10.5, 4.75, 2.2, 1.3, OUT, "GitHub", "All data, code and tests. One command rebuilds everything", "out-git");
    s.addShape(pres.shapes.LINE, { x: 10.35, y: 2.32, w: 0, h: 3.08, line: { color: AR, width: 2 }, objectName: "bracket-out" });
    [2.32, 3.87, 5.4].forEach((y, i) => arrow(10.35, y, 0.15, 0, `a-out-${i}`));

    say(s, "Every number on these slides is produced by this pipeline, and the deck itself is generated from its outputs.", { x: 0.6, y: 6.3, w: 9.5, h: 0.4, fontSize: 13 });
    s.addNotes("This is the whole system on one page. On the left, the data: the official INNOTHON dataset for population and GDP, the National Power Portal's generation by region, the power traded between regions, and national history. Everything is checked automatically; the regional numbers add up exactly to the national total. The demand model forecasts generation for India and each region, and I validate it against time-series and machine-learning models and stress-test it with 2,000 Monte Carlo runs. The optimiser then decides the cheapest mix for each region, and does it again for 2030, 2035 and 2040 to give the pathway. The results feed the live dashboard and the GitHub repository, where one command rebuilds everything from scratch.");
  }

  // ================================================================ 7 actions + close
  {
    const s = pres.addSlide({ masterName: "Dark" });
    s.addText("What India needs to do", { x: 0.7, y: 0.45, w: 11.9, h: 0.85, fontSize: 34, bold: true, color: K.onDark, margin: 0, isTextBox: true });
    const acts = [
      [Fa.FaSolarPanel, K.gold, "Build faster", "About 82 GW of solar and 23 GW of wind every year from the mid-2030s."],
      [Fa.FaProjectDiagram, K.hydro, "Connect the regions", "Triple the transmission lines between regions so sunny and windy areas can supply the East."],
      [Fa.FaAtom, K.nuclear, "Keep nuclear on time", `${fmt(D.nuc_gw)} GW of nuclear lets coal level off instead of growing.`],
      [Fa.FaBatteryFull, K.wind, "Store the sunshine", `About ${fmt(Math.round(D.bess / 10) * 10)} GW of batteries to carry daytime solar into the evening.`],
    ];
    for (let i = 0; i < 4; i++) {
      const [Ic, c, h, t] = acts[i]; const x = 0.7 + i * 3.05;
      s.addShape(pres.shapes.OVAL, { x, y: 1.6, w: 0.9, h: 0.9, fill: { color: "1C2B48" }, line: { type: "none" }, objectName: `act-ring-${i}` });
      s.addImage({ data: await icon(Ic, c), x: x + 0.22, y: 1.82, w: 0.46, h: 0.46, altText: h });
      s.addText(h, { x, y: 2.7, w: 2.8, h: 0.45, fontSize: 20, bold: true, color: K.onDark, margin: 0, isTextBox: true });
      s.addText(t, { x, y: 3.15, w: 2.75, h: 1.2, fontSize: 15, color: K.onDarkMuted, margin: 0, isTextBox: true, valign: "top" });
    }
    s.addText("Thank you", { x: 0.7, y: 4.65, w: 6, h: 0.6, fontSize: 28, bold: true, color: K.gold, margin: 0, isTextBox: true });
    s.addText([
      { text: "Try it live: ", options: { color: K.onDarkMuted } },
      { text: D.app, options: { color: K.gold, hyperlink: { url: D.app }, breakLine: true } },
      { text: "Code and data: ", options: { color: K.onDarkMuted } },
      { text: D.repo, options: { color: K.gold, hyperlink: { url: D.repo } } },
    ], { x: 0.7, y: 5.3, w: 8.5, h: 0.75, fontSize: 14, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 3 });
    s.addText([{ text: "Ashish Manash", options: { bold: true, color: K.onDark, breakLine: true } }, { text: "Team Innovexa, NIT Karnataka", options: { color: K.onDarkMuted } }],
      { x: 9.3, y: 5.3, w: 3.4, h: 0.75, fontSize: 14, margin: 0, isTextBox: true, align: "right", valign: "top" });
    s.addText("AI use: I used Claude (Anthropic) to help with data gathering, coding and drafting, as the competition terms ask us to disclose.",
      { x: 0.7, y: 6.35, w: 11, h: 0.35, fontSize: 11, color: K.onDarkMuted, margin: 0, isTextBox: true });
    s.addNotes("Four things follow from the model. Build solar and wind faster than India ever has. Connect the regions with much bigger transmission lines. Keep the nuclear programme on schedule. And store the sunshine in batteries. Thank you. I'd now like to show you the live dashboard, where you can change any assumption and watch the forecast and the regional plan re-run.");
  }

  await pres.writeFile({ fileName: "India_2047_Electricity_INNOTHON_Final.pptx" });
  if (applyTheme) await applyTheme("India_2047_Electricity_INNOTHON_Final.pptx", THEME);
  console.log("written");
})();
