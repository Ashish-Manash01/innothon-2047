// India 2047 electricity forecast — page logic. Every number is read from a dataset or a dash.calc below.

// ---------------------------------------------------------------- calculations (readers see these in Sources)
dash.calc('growth', {
  title: '2047 growth vs FY26 actual',
  description: '2047 total generation divided by FY26 actual generation, and the implied annual growth over 21 years.',
  inputs: ['demand_paths', 'history'],
  fn: (demand_paths, history) => {
    const g26 = Number(history.find((h) => Number(h.fy_end) === 2026).generation_twh);
    return demand_paths.filter((r) => Number(r.fy_end) === 2047).map((r) => ({
      scenario: r.scenario, gen_total_2047: Number(r.gen_total), multiple: Number(r.gen_total) / g26,
      cagr_pct: (Math.pow(Number(r.gen_total) / g26, 1 / 21) - 1) * 100,
    }));
  },
});

dash.calc('delta', {
  title: 'Change vs base demand',
  description: '2047 total generation of each scenario minus the base scenario (6.5% GDP, estimated elasticity, base new loads).',
  inputs: ['demand_paths'],
  fn: (demand_paths) => {
    const y = demand_paths.filter((r) => Number(r.fy_end) === 2047);
    const base = Number(y.find((r) => r.scenario === 'g65_bbase_evbase_dcbase_h2base').gen_total);
    return y.map((r) => ({ scenario: r.scenario, delta_twh: Number(r.gen_total) - base, delta_pct: (Number(r.gen_total) / base - 1) * 100 }));
  },
});

dash.calc('mix_nat', {
  title: 'National mix by scenario',
  description: 'Regional generation summed to India, with each source as a share of the national total.',
  inputs: ['mix_regional'],
  fn: (mix_regional) => {
    const tot = {}, by = {};
    for (const r of mix_regional) {
      const k = r.scenario + '|' + r.source;
      tot[r.scenario] = (tot[r.scenario] || 0) + Number(r.twh);
      by[k] = by[k] || { scenario: r.scenario, source: r.source, twh: 0, gw: 0 };
      by[k].twh += Number(r.twh); by[k].gw += Number(r.gw);
    }
    return Object.values(by).map((d) => ({ ...d, share_pct: d.twh / tot[d.scenario] * 100 }));
  },
});

dash.calc('mix_reg', {
  title: 'Regional mix by scenario',
  description: "Each region's generation by source as a share of that region's total, and capacity by source.",
  inputs: ['mix_regional'],
  fn: (mix_regional) => {
    const by = {};
    for (const r of mix_regional) {
      const k = r.scenario + '|' + r.region;
      by[k] = by[k] || { scenario: r.scenario, region: r.region, total_twh: 0 };
      by[k][r.source + '_twh'] = Number(r.twh); by[k][r.source + '_gw'] = Number(r.gw);
      by[k].total_twh += Number(r.twh);
    }
    const src = ['coal', 'gas', 'nuclear', 'hydro', 'solar', 'wind'];
    return Object.values(by).map((d) => {
      for (const s of src) d[s + '_pct'] = d.total_twh > 0 ? d[s + '_twh'] / d.total_twh * 100 : 0;
      return d;
    });
  },
});

// ---------------------------------------------------------------- shared helpers
window.IX = (() => {
  const SRC = ['coal', 'gas', 'nuclear', 'hydro', 'solar', 'wind'];
  const LAB = { coal: 'Coal', gas: 'Gas', nuclear: 'Nuclear', hydro: 'Hydro', solar: 'Solar', wind: 'Wind', bess: 'Batteries' };
  const REG = ['Northern', 'Western', 'Southern', 'Eastern', 'North-Eastern'];
  const BASE_D = 'g65_bbase_evbase_dcbase_h2base';
  const BASE_M = 'co21200_leastcost_rebase_dbase';
  const f0 = d3.format(',.0f'), f1 = d3.format(',.1f'), f2 = d3.format(',.2f');
  const sf0 = (v) => (v > 0 ? '+' : '') + f0(v);
  const num = (v) => (v === '' || v === null || v === undefined || Number.isNaN(Number(v)) ? null : Number(v));
  const rows = (id) => { const g = dash.data(id); return g.status === 'ok' ? g.data : null; };
  const P = () => dash.params();
  const dId = () => { const p = P(); return `g${Math.round(Number(p.gdp) * 10)}_b${p.el}_ev${p.ev}_dc${p.dc}_h2${p.h2}`; };
  const mId = () => { const p = P(); return `co2${p.co2}_${p.nuc}_re${p.re}_d${p.dem}`; };
  const color = (el, name) => getComputedStyle(el).getPropertyValue('--ix-' + name).trim() || '#888';
  const tokenColor = (el, v) => getComputedStyle(el).getPropertyValue(v).trim() || '#888';

  function findRow(data, where) {
    return data.find((r) => Object.entries(where).every(([k, v]) => String(r[k]) === String(v)));
  }
  // Fill one number element. where: object of column -> value; written to data-where so Sources can cite the cell.
  function fillNum(el, id, where, fmt) {
    const e = (v) => String(v).replace(/%/g, '%25').replace(/&/g, '%26').replace(/=/g, '%3D');
    el.dataset.where = Object.entries(where).map(([k, v]) => `${e(k)}=${e(v)}`).join('&');
    const d = rows(id);
    const row = d && findRow(d, where);
    const v = row ? num(row[el.dataset.field]) : null;
    el.textContent = v === null ? '—' : fmt(v);
  }

  function svgIn(el, H) {
    el.replaceChildren();
    const W = Math.max(280, el.clientWidth || 600);
    const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img');
    return { svg, W, H };
  }
  function textWidth(svg, strings) {
    const t = svg.append('text').attr('class', 'measure');
    let w = 0;
    for (const s of strings) { t.text(s); w = Math.max(w, t.node().getComputedTextLength()); }
    t.remove();
    return w;
  }
  function tipBox(el) {
    const t = document.createElement('div'); t.className = 'ix-tip'; t.hidden = true; el.appendChild(t);
    return {
      show(head, lines, x, y) {
        t.replaceChildren();
        const h = document.createElement('div'); h.className = 'hd'; h.textContent = head; t.appendChild(h);
        for (const [c, name, val] of lines) {
          const ln = document.createElement('div'); ln.className = 'ln';
          if (c) { const sw = document.createElement('i'); sw.className = 'ix-sw'; sw.style.background = c; ln.appendChild(sw); }
          const a = document.createElement('span'); a.textContent = name; ln.appendChild(a);
          const b = document.createElement('span'); b.textContent = val; ln.appendChild(b);
          t.appendChild(ln);
        }
        t.hidden = false;
        const W = el.clientWidth, tw = t.offsetWidth, th = t.offsetHeight;
        t.style.left = Math.max(0, Math.min(W - tw, x + 12)) + 'px';
        t.style.top = Math.max(0, y - th - 8) + 'px';
      },
      hide() { t.hidden = true; },
    };
  }
  function yAxis(g, y, W, m, fmt) {
    const ax = g.append('g').attr('class', 'axis').attr('transform', `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(fmt).tickSize(0)).attr('font-size', null).attr('font-family', null);
    ax.select('.domain').remove();
    g.append('g').attr('class', 'grid').selectAll('line').data(y.ticks(5)).join('line')
      .attr('x1', m.l).attr('x2', W - m.r).attr('y1', (d) => y(d)).attr('y2', (d) => y(d));
    ax.selectAll('text').attr('dx', '-6');
  }

  // Lines over years. series: [{name, color, pts:[{x,y}], dash}], band: {pts:[{x,lo,hi}], color}
  function lines(el, { series, band, H = 290, yfmt = f0, unit = 'TWh', x0, x1 }) {
    const { svg, W } = svgIn(el, H);
    const all = series.flatMap((s) => s.pts).concat(band ? band.pts.map((p) => ({ x: p.x, y: p.hi })) : []);
    if (!all.length) { el.textContent = '—'; return; }
    const ymax = d3.max(all, (p) => p.y) * 1.08;
    const y = d3.scaleLinear([0, ymax], [H - 26, 10]).nice();
    const m = { l: textWidth(svg, y.ticks(5).map(yfmt)) + 14, r: 14 };
    const xs = all.map((p) => p.x);
    const x = d3.scaleLinear([x0 ?? d3.min(xs), x1 ?? d3.max(xs)], [m.l, W - m.r]);
    yAxis(svg, y, W, m, yfmt);
    const xa = svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - 26})`)
      .call(d3.axisBottom(x).ticks(Math.min(8, Math.floor(W / 80))).tickFormat((d) => 'FY' + String(d).slice(2)).tickSizeOuter(0))
      .attr('font-size', null).attr('font-family', null);
    xa.selectAll('text').attr('dy', '1em');
    if (band && band.pts.length) {
      svg.append('path').datum(band.pts).attr('fill', band.color).attr('opacity', 0.18)
        .attr('d', d3.area().x((p) => x(p.x)).y0((p) => y(p.lo)).y1((p) => y(p.hi)));
    }
    for (const s of series) {
      svg.append('path').datum(s.pts).attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', s.width || 2)
        .attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round').attr('stroke-dasharray', s.dash ? '5,4' : null)
        .attr('d', d3.line().defined((p) => p.y !== null).x((p) => x(p.x)).y((p) => y(p.y)));
    }
    const tip = tipBox(el);
    const years = Array.from(new Set(xs)).sort((a, b) => a - b);
    const dot = svg.append('g');
    svg.append('rect').attr('x', m.l).attr('y', 0).attr('width', W - m.l - m.r).attr('height', H - 26).attr('fill', 'transparent')
      .on('mousemove', (ev) => {
        const [mx, my] = d3.pointer(ev);
        const yr = years.reduce((a, b) => (Math.abs(x(b) - mx) < Math.abs(x(a) - mx) ? b : a));
        const ls = [];
        dot.selectAll('*').remove();
        for (const s of series) {
          const p = s.pts.find((q) => q.x === yr);
          if (p && p.y !== null) { ls.push([s.color, s.name, yfmt(p.y) + ' ' + unit]); dot.append('circle').attr('cx', x(yr)).attr('cy', y(p.y)).attr('r', 3.5).attr('fill', s.color); }
        }
        if (band) { const b = band.pts.find((q) => q.x === yr); if (b) ls.push([null, 'P10–P90', `${yfmt(b.lo)}–${yfmt(b.hi)} ${unit}`]); }
        if (!ls.length) { tip.hide(); return; }
        tip.show(`FY${yr - 1}-${String(yr).slice(2)}`, ls, mx, my);
      })
      .on('mouseleave', () => { tip.hide(); dot.selectAll('*').remove(); });
  }

  // Vertical stacked bars. cats: labels; val(cat, key) -> number; pct: normalise to 100
  function vstack(el, { cats, keys, val, colors, names, H = 290, pct = false, catLabel = (c) => c }) {
    const { svg, W } = svgIn(el, H);
    const data = cats.map((c) => { const o = { cat: c }; let t = 0; for (const k of keys) { o[k] = val(c, k) || 0; t += o[k]; } if (pct) for (const k of keys) o[k] = t ? o[k] / t * 100 : 0; o._t = t; return o; });
    const stack = d3.stack().keys(keys)(data);
    const yfmt = pct ? ((v) => v + '%') : f0;
    const ymax = pct ? 100 : d3.max(data, (d) => keys.reduce((a, k) => a + d[k], 0)) * 1.05;
    const y = d3.scaleLinear([0, ymax], [H - 26, 10]); if (!pct) y.nice();
    const m = { l: textWidth(svg, y.ticks(5).map(yfmt)) + 14, r: 8 };
    const x = d3.scaleBand(cats, [m.l, W - m.r]).padding(0.28);
    yAxis(svg, y, W, m, yfmt);
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - 26})`)
      .call(d3.axisBottom(x).tickFormat(catLabel).tickSizeOuter(0)).attr('font-size', null).attr('font-family', null).selectAll('text').attr('dy', '1em');
    const bw = Math.min(x.bandwidth(), 56), off = (x.bandwidth() - bw) / 2;
    svg.append('g').selectAll('g').data(stack).join('g').attr('fill', (s) => colors[s.key])
      .selectAll('rect').data((s) => s).join('rect')
      .attr('x', (d) => x(d.data.cat) + off).attr('width', bw).attr('y', (d) => y(d[1])).attr('height', (d) => Math.max(0, y(d[0]) - y(d[1])));
    const tip = tipBox(el);
    svg.append('g').selectAll('rect').data(data).join('rect').attr('x', (d) => x(d.cat)).attr('width', x.bandwidth())
      .attr('y', 0).attr('height', H - 26).attr('fill', 'transparent')
      .on('mousemove', (ev, d) => {
        const [mx, my] = d3.pointer(ev, el);
        tip.show(catLabel(d.cat), keys.slice().reverse().map((k) => [colors[k], names[k], pct ? f1(d[k]) + '%' : f0(d[k]) + ' TWh']), mx, my);
      })
      .on('mouseleave', () => tip.hide());
  }

  // Horizontal stacked bars (regions), TWh
  function hstack(el, { cats, keys, val, colors, names, unit = 'TWh' }) {
    const rowH = 30, H = cats.length * rowH + 30;
    const { svg, W } = svgIn(el, H);
    const data = cats.map((c) => { const o = { cat: c }; for (const k of keys) o[k] = val(c, k) || 0; o._t = keys.reduce((a, k) => a + o[k], 0); return o; });
    const stack = d3.stack().keys(keys)(data);
    const m = { l: textWidth(svg, cats) + 12, r: textWidth(svg, data.map((d) => f0(d._t))) + 14 };
    const x = d3.scaleLinear([0, d3.max(data, (d) => d._t) || 1], [m.l, W - m.r]).nice();
    const y = d3.scaleBand(cats, [6, H - 24]).padding(0.25);
    svg.append('g').attr('class', 'grid').selectAll('line').data(x.ticks(5)).join('line').attr('x1', (d) => x(d)).attr('x2', (d) => x(d)).attr('y1', 6).attr('y2', H - 24);
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(5).tickFormat(f0).tickSize(0))
      .attr('font-size', null).attr('font-family', null).call((g) => g.select('.domain').remove()).selectAll('text').attr('dy', '1em');
    svg.append('g').selectAll('text').data(cats).join('text').attr('class', 'lbl').attr('x', m.l - 8).attr('y', (c) => y(c) + y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'end').text((c) => c);
    svg.append('g').selectAll('g').data(stack).join('g').attr('fill', (s) => colors[s.key]).selectAll('rect').data((s) => s).join('rect')
      .attr('y', (d) => y(d.data.cat)).attr('height', y.bandwidth()).attr('x', (d) => x(d[0])).attr('width', (d) => Math.max(0, x(d[1]) - x(d[0])));
    svg.append('g').selectAll('text').data(data).join('text').attr('x', (d) => x(d._t) + 6).attr('y', (d) => y(d.cat) + y.bandwidth() / 2).attr('dy', '0.35em').text((d) => f0(d._t));
    const tip = tipBox(el);
    svg.append('g').selectAll('rect').data(data).join('rect').attr('x', m.l).attr('width', W - m.l - m.r).attr('y', (d) => y(d.cat)).attr('height', y.bandwidth()).attr('fill', 'transparent')
      .on('mousemove', (ev, d) => {
        const [mx, my] = d3.pointer(ev, el);
        tip.show(`${d.cat}: ${f0(d._t)} ${unit}`, keys.slice().reverse().filter((k) => d[k] > 0.05).map((k) => [colors[k], names[k], `${f0(d[k])} ${unit} · ${f1(d._t ? d[k] / d._t * 100 : 0)}%`]), mx, my);
      })
      .on('mouseleave', () => tip.hide());
  }

  // Horizontal diverging bars. items: [{label, lo, hi}] or single value {label, v}
  function hdiverge(el, { items, loColor, hiColor, unit = 'TWh', twoSided = true }) {
    const rowH = 28, H = items.length * rowH + 30;
    const { svg, W } = svgIn(el, H);
    const vals = items.flatMap((d) => (twoSided ? [d.lo, d.hi] : [d.v]));
    const ext = d3.max(vals.map(Math.abs)) || 1;
    const m = { l: textWidth(svg, items.map((d) => d.label)) + 12, r: 46 };
    const x = d3.scaleLinear([-ext * 1.1, ext * 1.1], [m.l + 40, W - m.r]).nice();
    const y = d3.scaleBand(items.map((d) => d.label), [6, H - 24]).padding(0.25);
    svg.append('g').attr('class', 'grid').selectAll('line').data(x.ticks(5)).join('line').attr('x1', (d) => x(d)).attr('x2', (d) => x(d)).attr('y1', 6).attr('y2', H - 24);
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(5).tickFormat(sf0).tickSize(0))
      .attr('font-size', null).attr('font-family', null).call((g) => g.select('.domain').remove()).selectAll('text').attr('dy', '1em');
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 2).attr('y2', H - 24).attr('stroke', tokenColor(el, '--cds-chart-reference'));
    svg.append('g').selectAll('text').data(items).join('text').attr('class', 'lbl').attr('x', m.l).attr('y', (d) => y(d.label) + y.bandwidth() / 2).attr('dy', '0.35em').text((d) => d.label);
    const bar = (v, c) => (g) => g.append('rect').attr('fill', c).attr('rx', 2).attr('height', y.bandwidth())
      .attr('x', (d) => x(Math.min(0, v(d)))).attr('width', (d) => Math.abs(x(v(d)) - x(0))).attr('y', (d) => y(d.label));
    const g = svg.append('g').selectAll('g').data(items).join('g');
    if (twoSided) { g.call(bar((d) => d.lo, loColor)); g.call(bar((d) => d.hi, hiColor)); }
    else g.call(bar((d) => d.v, hiColor));
    const tip = tipBox(el);
    svg.append('g').selectAll('rect').data(items).join('rect').attr('x', m.l).attr('width', W - m.l - m.r).attr('y', (d) => y(d.label)).attr('height', y.bandwidth()).attr('fill', 'transparent')
      .on('mousemove', (ev, d) => {
        const [mx, my] = d3.pointer(ev, el);
        tip.show(d.label, twoSided ? [[loColor, 'Low value', sf0(d.lo) + ' ' + unit], [hiColor, 'High value', sf0(d.hi) + ' ' + unit]] : [[hiColor, 'Net', sf0(d.v) + ' ' + unit]], mx, my);
      })
      .on('mouseleave', () => tip.hide());
  }

  // Grouped vertical bars: cats x series
  function vgroup(el, { cats, series, val, colors, H = 240, catLabel = (c) => c, unit = 'TWh' }) {
    const { svg, W } = svgIn(el, H);
    const vmax = d3.max(cats.flatMap((c) => series.map((s) => val(c, s) || 0))) * 1.08 || 1;
    const y = d3.scaleLinear([0, vmax], [H - 26, 10]).nice();
    const m = { l: textWidth(svg, y.ticks(5).map(f0)) + 14, r: 8 };
    const x = d3.scaleBand(cats, [m.l, W - m.r]).padding(0.22);
    const xi = d3.scaleBand(series, [0, x.bandwidth()]).padding(0.12);
    yAxis(svg, y, W, m, f0);
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - 26})`).call(d3.axisBottom(x).tickFormat(catLabel).tickSizeOuter(0))
      .attr('font-size', null).attr('font-family', null).selectAll('text').attr('dy', '1em');
    const bw = Math.min(xi.bandwidth(), 32), off = (xi.bandwidth() - bw) / 2;
    const g = svg.append('g').selectAll('g').data(cats).join('g').attr('transform', (c) => `translate(${x(c)},0)`);
    g.selectAll('rect').data((c) => series.map((s) => ({ c, s, v: val(c, s) || 0 }))).join('rect')
      .attr('x', (d) => xi(d.s) + off).attr('width', bw).attr('y', (d) => y(d.v)).attr('height', (d) => Math.max(0, y(0) - y(d.v))).attr('rx', 2).attr('fill', (d) => colors[d.s]);
    const tip = tipBox(el);
    svg.append('g').selectAll('rect').data(cats).join('rect').attr('x', (c) => x(c)).attr('width', x.bandwidth()).attr('y', 0).attr('height', H - 26).attr('fill', 'transparent')
      .on('mousemove', (ev, c) => { const [mx, my] = d3.pointer(ev, el); tip.show(catLabel(c), series.map((s) => [colors[s], s, f0(val(c, s) || 0) + ' ' + unit]), mx, my); })
      .on('mouseleave', () => tip.hide());
  }

  // Table body from rows. cols: [{f, fmt?, cls?}]; key: fn(row) -> data-key string
  function tbody(el, data, cols, key, cls) {
    el.replaceChildren();
    if (!data) return;
    for (const r of data) {
      const tr = document.createElement('tr');
      if (key) tr.dataset.key = key(r);
      if (cls) { const c = cls(r); if (c) tr.className = c; }
      for (const c of cols) {
        const td = document.createElement('td');
        const v = r[c.f];
        td.textContent = c.fmt ? (num(v) === null && c.numeric !== false ? '—' : c.fmt(v, r)) : (v ?? '');
        if (c.cls) td.className = typeof c.cls === 'function' ? c.cls(v, r) : c.cls;
        tr.appendChild(td);
      }
      el.appendChild(tr);
    }
  }

  return { SRC, LAB, REG, BASE_D, BASE_M, f0, f1, f2, sf0, num, rows, P, dId, mId, color, tokenColor, fillNum, lines, vstack, hstack, hdiverge, vgroup, tbody };
})();

// ---------------------------------------------------------------- tabs, controls (listen and set value / hidden only)
(() => {
  const TABS = ['overview', 'demand', 'mix', 'pathway', 'validation', 'assumptions'];
  const DEMAND_DEFAULTS = { gdp: '6.5', el: 'base', ev: 'base', dc: 'base', h2: 'base' };
  const MIX_DEFAULTS = { co2: '1200', nuc: 'leastcost', re: 'base', dem: 'base' };
  document.querySelectorAll('.ix-tab').forEach((b) => b.addEventListener('click', () => {
    dash.setParams({ tab: b.dataset.tab }); dash.setLink(b.dataset.tab);
  }));
  document.querySelectorAll('select[data-param]').forEach((s) => s.addEventListener('change', () => dash.setParams({ [s.dataset.param]: s.value })));
  document.querySelectorAll('[data-reset]').forEach((b) => b.addEventListener('click', () => dash.setParams(b.dataset.reset === 'demand' ? DEMAND_DEFAULTS : MIX_DEFAULTS)));
  document.querySelectorAll('.ix-search').forEach((inp) => inp.addEventListener('input', () => { window.IX_SEARCH = inp.value.trim().toLowerCase(); dash.draw('tb_assump'); }));
  const hash = location.hash.slice(1);
  if (TABS.includes(hash)) dash.setParams({ tab: hash });
  dash.onData(() => {
    const p = dash.params();
    const tab = TABS.includes(p.tab) ? p.tab : 'overview';
    document.querySelectorAll('[data-tab-page]').forEach((s) => { s.hidden = s.dataset.tabPage !== tab; });
    document.querySelectorAll('.ix-tab').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === tab)));
    document.querySelectorAll('select[data-param]').forEach((s) => { const v = p[s.dataset.param]; if (v !== undefined && v !== null) s.value = String(v); });
  });
})();

// ---------------------------------------------------------------- numbers
(() => {
  const { f0, f1, f2, sf0, fillNum, dId, mId, BASE_D, BASE_M } = window.IX;
  const N = [
    ['t_total', 'demand_paths', () => ({ scenario: BASE_D, fy_end: 2047 }), f0],
    ['t_p10', 'mc_fan', () => ({ fy_end: 2047, measure: 'gen_total' }), f0],
    ['t_p90', 'mc_fan', () => ({ fy_end: 2047, measure: 'gen_total' }), f0],
    ['t_mult', 'growth', () => ({ scenario: BASE_D }), f1],
    ['t_nf', 'mix_summary', () => ({ scenario: BASE_M }), f1],
    ['k_total', 'demand_paths', () => ({ scenario: BASE_D, fy_end: 2047 }), f0],
    ['k_grid', 'demand_paths', () => ({ scenario: BASE_D, fy_end: 2047 }), f0],
    ['k_cagr', 'growth', () => ({ scenario: BASE_D }), f1],
    ['k_nf', 'mix_summary', () => ({ scenario: BASE_M }), f1],
    ['k_nf26', 'pathway_nat', () => ({ fy_end: 2026 }), f1],
    ['k_co2', 'mix_summary', () => ({ scenario: BASE_M }), f0],
    ['k_co226', 'pathway_nat', () => ({ fy_end: 2026 }), f0],
    ['k_cost', 'mix_summary', () => ({ scenario: BASE_M }), f2],
    ['d_b', 'panel', () => ({ spec: '1 Main (state FE, clustered SE)' }), (v) => d3.format('.3f')(v)],
    ['dk_total', 'demand_paths', () => ({ scenario: dId(), fy_end: 2047 }), f0],
    ['dk_delta', 'delta', () => ({ scenario: dId() }), sf0],
    ['dk_cagr', 'growth', () => ({ scenario: dId() }), f1],
    ['dk_mult', 'growth', () => ({ scenario: dId() }), f1],
    ['dk_grid', 'demand_paths', () => ({ scenario: dId(), fy_end: 2047 }), f0],
    ['dk_evdc', 'demand_paths', () => ({ scenario: dId(), fy_end: 2047 }), f0],
    ['dk_h2', 'demand_paths', () => ({ scenario: dId(), fy_end: 2047 }), f0],
    ['mk_nf', 'mix_summary', () => ({ scenario: mId() }), f1],
    ['mk_tot', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mk_co2', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mk_cost', 'mix_summary', () => ({ scenario: mId() }), f2],
    ['mk_cp', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mk_bess', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mk_psp', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mw_uns', 'mix_summary', () => ({ scenario: mId() }), f0],
    ['mw_co2', 'mix_summary', () => ({ scenario: mId() }), f0],
  ];
  for (const [name, id, where, fmt] of N) dash.draw(name, (el) => fillNum(el, id, where(), fmt));
  // which warning sentences apply to the selected mix setting
  dash.draw('m_warnctl', (el) => {
    el.replaceChildren();
    const d = window.IX.rows('mix_summary');
    const r = d && d.find((x) => x.scenario === mId());
    document.querySelectorAll('[data-warn]').forEach((p) => {
      const v = r ? Number(r[p.dataset.warn === 'unserved' ? 'unserved_twh' : 'co2_over_cap_mt']) : 0;
      p.hidden = !(v > 0.5);
    });
  });
})();

// ---------------------------------------------------------------- charts
(() => {
  const X = window.IX;
  const { SRC, LAB, REG, BASE_D, BASE_M, num, rows, dId, mId, color } = X;
  const srcColors = (el) => Object.fromEntries(SRC.concat(['bess']).map((s) => [s, color(el, s)]));
  const fg = (el) => X.tokenColor(el, '--color-fg');

  function fanSeries(el, scen, selected) {
    const h = rows('history'), d = rows('demand_paths'), q = rows('mc_fan');
    if (!h || !d || !q) { el.replaceChildren(); el.textContent = '—'; return null; }
    const path = (sid, col) => d.filter((r) => r.scenario === sid).map((r) => ({ x: Number(r.fy_end), y: Number(r[col]) }));
    const band = { color: color(el, 'hydro'), pts: q.filter((r) => r.measure === 'gen_total').map((r) => ({ x: Number(r.fy_end), lo: Number(r.p10), hi: Number(r.p90) })).sort((a, b) => a.x - b.x) };
    const hist = { name: 'Actual', color: fg(el), pts: h.map((r) => ({ x: Number(r.fy_end), y: Number(r.generation_twh) })) };
    return { h: hist, band, path };
  }

  dash.draw('ch_fan', (el) => {
    const s = fanSeries(el); if (!s) return;
    X.lines(el, { band: s.band, series: [s.h,
      { name: 'Base: total incl. H₂', color: color(el, 'hydro'), pts: s.path(BASE_D, 'gen_total') },
      { name: 'Base: grid only', color: X.tokenColor(el, '--color-fg-muted'), pts: s.path(BASE_D, 'gen_grid'), dash: true }] });
  });

  dash.draw('ch_dpath', (el) => {
    const s = fanSeries(el); if (!s) return;
    X.lines(el, { band: s.band, series: [s.h,
      { name: 'Base', color: X.tokenColor(el, '--color-fg-muted'), pts: s.path(BASE_D, 'gen_total'), dash: true },
      { name: 'Selected', color: color(el, 'bess'), pts: s.path(dId(), 'gen_total'), width: 2.5 }] });
  });

  dash.draw('ch_decomp', (el) => {
    const d = rows('demand_paths'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const r = d.filter((x) => x.scenario === dId()).map((x) => ({ y: Number(x.fy_end), a: Number(x.gen_organic), b: Number(x.gen_ev_dc), c: Number(x.gen_h2) }));
    const cats = r.map((x) => String(x.y)).filter((y) => Number(y) % 3 === 2 || y === '2047' || y === '2026');
    const look = Object.fromEntries(r.map((x) => [String(x.y), x]));
    const colors = { a: color(el, 'hydro'), b: color(el, 'bess'), c: color(el, 'wind') };
    X.vstack(el, { cats, keys: ['a', 'b', 'c'], val: (c, k) => look[c][k], colors, names: { a: 'Organic demand', b: 'EVs + data centres', c: 'Green hydrogen' },
      catLabel: (c) => 'FY' + c.slice(2) });
  });

  dash.draw('ch_dreg', (el) => {
    const d = rows('demand_regional'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const sel = d.filter((x) => x.scenario === dId());
    const yrs = ['2030', '2035', '2040', '2047'];
    const look = {}; for (const x of sel) look[x.region + '|' + x.fy_end] = Number(x.gen_total_twh);
    const colors = { 2030: X.tokenColor(el, '--cds-chart-muted'), 2035: color(el, 'gas'), 2040: color(el, 'hydro'), 2047: color(el, 'bess') };
    const short = { Northern: 'North', Western: 'West', Southern: 'South', Eastern: 'East', 'North-Eastern': 'NE' };
    X.vgroup(el, { cats: REG, series: yrs, val: (c, s) => look[c + '|' + s], colors, catLabel: (c) => short[c], H: 260 });
  });

  dash.draw('ch_tornado', (el) => {
    const d = rows('tornado'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const items = d.map((r) => ({ label: r.driver, lo: Number(r.low), hi: Number(r.high), span: Number(r.span) })).sort((a, b) => b.span - a.span);
    X.hdiverge(el, { items, loColor: X.tokenColor(el, '--cds-chart-muted'), hiColor: color(el, 'hydro') });
  });

  dash.draw('ch_pathshare', (el) => {
    const d = rows('pathway_nat'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const look = Object.fromEntries(d.map((r) => [String(r.fy_end), r]));
    X.vstack(el, { cats: d.map((r) => String(r.fy_end)), keys: SRC, val: (c, k) => num(look[c][k + '_twh']), colors: srcColors(el), names: LAB, pct: true,
      catLabel: (c) => 'FY' + c.slice(2) + (look[c].kind === 'actual' ? ' (actual)' : '') });
  });

  dash.draw('ch_ptwh', (el) => {
    const d = rows('pathway_nat'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const look = Object.fromEntries(d.map((r) => [String(r.fy_end), r]));
    X.vstack(el, { cats: d.map((r) => String(r.fy_end)), keys: SRC, val: (c, k) => num(look[c][k + '_twh']), colors: srcColors(el), names: LAB,
      catLabel: (c) => 'FY' + c.slice(2) });
  });

  dash.draw('ch_pcap', (el) => {
    const d = rows('pathway_nat'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const keys = ['coal', 'nuclear', 'hydro', 'solar', 'wind', 'bess'];
    X.lines(el, { unit: 'GW', series: keys.map((k) => ({ name: LAB[k], color: color(el, k), pts: d.map((r) => ({ x: Number(r.fy_end), y: num(r[k + '_gw']) })).filter((p) => p.y !== null) })) });
  });

  dash.draw('ch_pco2', (el) => {
    const d = rows('pathway_nat'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    X.lines(el, { unit: 'Mt', H: 230, series: [
      { name: 'Emissions', color: fg(el), pts: d.map((r) => ({ x: Number(r.fy_end), y: num(r.co2_mt) })) },
      { name: 'Cap', color: X.tokenColor(el, '--color-fg-muted'), dash: true, pts: d.map((r) => ({ x: Number(r.fy_end), y: num(r.co2_cap_mt) })).filter((p) => p.y !== null) }] });
  });

  const regChart = (el, data) => {
    const look = {}; for (const r of data) look[r.region + '|' + r.source] = Number(r.twh);
    X.hstack(el, { cats: REG, keys: SRC, val: (c, k) => look[c + '|' + k], colors: srcColors(el), names: LAB });
  };
  dash.draw('ch_regbase', (el) => { const d = rows('mix_regional'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; } regChart(el, d.filter((r) => r.scenario === BASE_M)); });
  dash.draw('ch_mreg', (el) => { const d = rows('mix_regional'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; } regChart(el, d.filter((r) => r.scenario === mId())); });
  dash.draw('ch_preg', (el) => {
    const d = rows('pathway_reg'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    regChart(el, d.filter((r) => String(r.fy_end) === String(dash.params().year || '2047')));
  });

  dash.draw('ch_mnat', (el) => {
    const d = rows('mix_nat'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const sel = d.filter((r) => r.scenario === mId());
    const items = SRC.map((s) => { const r = sel.find((x) => x.source === s); return { label: LAB[s], s, v: r ? r.share_pct : 0, twh: r ? r.twh : 0 }; });
    // one horizontal bar per source
    const rowH = 28, H = items.length * rowH + 30;
    el.replaceChildren();
    const W = Math.max(280, el.clientWidth || 600);
    const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const x = d3.scaleLinear([0, Math.max(50, d3.max(items, (i) => i.v))], [70, W - 110]);
    const y = d3.scaleBand(items.map((i) => i.label), [6, H - 10]).padding(0.25);
    svg.append('g').selectAll('text').data(items).join('text').attr('class', 'lbl').attr('x', 0).attr('y', (i) => y(i.label) + y.bandwidth() / 2).attr('dy', '0.35em').text((i) => i.label);
    svg.append('g').selectAll('rect').data(items).join('rect').attr('x', x(0)).attr('y', (i) => y(i.label)).attr('height', y.bandwidth()).attr('rx', 2)
      .attr('width', (i) => Math.max(0, x(i.v) - x(0))).attr('fill', (i) => color(el, i.s));
    svg.append('g').selectAll('text').data(items).join('text').attr('x', (i) => x(i.v) + 6).attr('y', (i) => y(i.label) + y.bandwidth() / 2).attr('dy', '0.35em')
      .text((i) => `${X.f1(i.v)}% · ${X.f0(i.twh)} TWh`);
  });

  dash.draw('ch_mnet', (el) => {
    const d = rows('mix_summary'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const r = d.find((x) => x.scenario === mId()); if (!r) { el.replaceChildren(); el.textContent = '—'; return; }
    const items = REG.map((g) => ({ label: g, v: Number(r['net_export_' + g.toLowerCase().replace('-', '_')]) }));
    X.hdiverge(el, { items, twoSided: false, hiColor: color(el, 'hydro') });
  });

  dash.draw('ch_back', (el) => {
    const d = rows('backcast'); if (!d) { el.replaceChildren(); el.textContent = '—'; return; }
    const nat = d.filter((r) => r.region === 'India');
    const look = Object.fromEntries(nat.map((r) => [r.source, r]));
    X.vgroup(el, { cats: SRC, series: ['Actual', 'Model'], val: (c, s) => Number(look[c] ? look[c][s === 'Actual' ? 'actual_twh' : 'model_twh'] : 0),
      colors: { Actual: X.tokenColor(el, '--cds-chart-muted'), Model: color(el, 'hydro') }, catLabel: (c) => LAB[c] });
  });
})();

// ---------------------------------------------------------------- tables
(() => {
  const X = window.IX;
  const { f0, f1, f2, SRC, REG, mId } = X;
  const enc = encodeURIComponent;
  const pc = (v) => f1(Number(v));
  const g0 = (v) => f0(Number(v));
  dash.draw('tb_mshare', (el) => {
    const d = X.rows('mix_reg'); const sel = d && d.filter((r) => r.scenario === mId()).sort((a, b) => REG.indexOf(a.region) - REG.indexOf(b.region));
    X.tbody(el, sel, [{ f: 'region' }, { f: 'total_twh', fmt: g0, cls: 'n' }].concat(SRC.map((s) => ({ f: s + '_pct', fmt: pc, cls: 'n' }))), (r) => enc(r.scenario) + ',' + enc(r.region));
  });
  dash.draw('tb_mcap', (el) => {
    const d = X.rows('mix_reg'); const sel = d && d.filter((r) => r.scenario === mId()).sort((a, b) => REG.indexOf(a.region) - REG.indexOf(b.region));
    X.tbody(el, sel, [{ f: 'region' }].concat(SRC.map((s) => ({ f: s + '_gw', fmt: (v) => f1(Number(v)), cls: 'n' }))), (r) => enc(r.scenario) + ',' + enc(r.region));
  });
  dash.draw('tb_path', (el) => {
    X.tbody(el, X.rows('pathway_nat'), [{ f: 'fy_end' }, { f: 'kind' }, { f: 'total_twh', fmt: g0, cls: 'n' }, { f: 'non_fossil_pct', fmt: pc, cls: 'n' },
      { f: 'co2_mt', fmt: g0, cls: 'n' }, { f: 'solar_gw', fmt: g0, cls: 'n' }, { f: 'wind_gw', fmt: g0, cls: 'n' }, { f: 'nuclear_gw', fmt: g0, cls: 'n' }, { f: 'coal_gw', fmt: g0, cls: 'n' }]);
  });
  dash.draw('tb_back', (el) => {
    const d = X.rows('backcast'); const sel = d && d.filter((r) => r.source === 'coal');
    X.tbody(el, sel, [{ f: 'region' }, { f: 'actual_twh', fmt: g0, cls: 'n' }, { f: 'model_twh', fmt: g0, cls: 'n' }, { f: 'diff_twh', fmt: (v) => X.sf0(Number(v)), cls: 'n' }],
      (r) => enc(r.region) + ',' + enc(r.source), (r) => (r.region === 'India' ? 'hl' : ''));
  });
  dash.draw('tb_bench', (el) => {
    X.tbody(el, X.rows('benchmarks'), [{ f: 'metric', cls: 'wrap' }, { f: 'estimate', cls: 'wrap' }, { f: 'value', fmt: (v) => d3.format(',.4~f')(Number(v)), cls: 'n' }, { f: 'source', cls: 'wrap' }],
      (r) => enc(r.metric) + ',' + enc(r.estimate), (r) => (r.estimate.startsWith('This model') ? 'hl' : ''));
  });
  dash.draw('tb_checks', (el) => {
    X.tbody(el, X.rows('checks'), [{ f: 'check', cls: 'wrap' }, { f: 'pass', fmt: (v) => (String(v) === 'True' ? '✓ Pass' : '✗ Fail'), numeric: false, cls: (v) => (String(v) === 'True' ? 'ix-pass' : 'ix-fail') }, { f: 'detail', cls: 'wrap' }]);
  });
  dash.draw('tb_panel', (el) => {
    const f3 = (v) => d3.format('.3f')(Number(v)), f4 = (v) => d3.format('.4f')(Number(v));
    X.tbody(el, X.rows('panel'), [{ f: 'spec', cls: 'wrap' }, { f: 'income_elasticity_b', fmt: f3, cls: 'n' }, { f: 'se_b', fmt: f3, cls: 'n' }, { f: 'urban_semi_elast_c', fmt: f4, cls: 'n' }, { f: 'n', fmt: g0, cls: 'n' }]);
  });
  dash.draw('tb_assump', (el) => {
    const d = X.rows('assumptions'); const q = window.IX_SEARCH || '';
    const sel = d && (q ? d.filter((r) => [r.item, r.basis, r.model, r.unit].join(' ').toLowerCase().includes(q)) : d);
    X.tbody(el, sel, [{ f: 'item', cls: 'wrap' }, { f: 'value', cls: 'n' }, { f: 'unit' }, { f: 'basis', cls: 'wrap' }, { f: 'model' }]);
  });
  dash.draw('tb_res', (el) => {
    const d = X.rows('resources'); const sel = d && d.slice().sort((a, b) => REG.indexOf(a.region) - REG.indexOf(b.region));
    X.tbody(el, sel, [{ f: 'region' }, { f: 'solar_potential_gw', fmt: g0, cls: 'n' }, { f: 'solar_used_2047_gw', fmt: g0, cls: 'n' }, { f: 'wind_potential_gw', fmt: g0, cls: 'n' },
      { f: 'wind_used_2047_gw', fmt: g0, cls: 'n' }, { f: 'hydro_potential_gw', fmt: g0, cls: 'n' }, { f: 'hydro_used_2047_gw', fmt: g0, cls: 'n' }]);
  });
  dash.draw('tb_src', (el) => {
    X.tbody(el, X.rows('sources_list'), [{ f: 'source', cls: 'wrap' }, { f: 'used_for', cls: 'wrap' }, { f: 'link' }]);
  });
})();
