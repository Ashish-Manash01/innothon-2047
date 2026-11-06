# Generation-mix model v1: India, FY2046-47

> **Update (6 Nov, evening):** the model now gives each region's coal fleet three cost tiers (−₹0.6 / 0 / +₹0.6 per kWh), calibrated on a FY26 backcast (regional coal error 25.6% → 5.9%). The national mix is unchanged. The regional split moved:
> - North 1,679 TWh (solar 73%), exports 204
> - West 1,872 TWh (solar 45%, coal 29%, wind 23%), exports 66
> - South 1,548 TWh (wind 40%, nuclear 21%), exports 14
> - East 441 TWh (coal 61%, nuclear 37%), imports 225
> - North-East 117 TWh (hydro 96%), exports 47
>
> The 2026–2047 pathway, the backcast and the full write-up are in the methodology doc. Where the tables below disagree, the methodology doc is current.

**What it answers:** given the v1 demand forecast by region, which mix of coal, gas, nuclear, hydro, solar and wind
should each of the 5 CEA regions generate in 2047, at least cost, within resource, build-rate, grid, reliability and
climate limits? The metric is **energy generated (TWh)**.

## Method (model/mix_lp.py: linear programme, PuLP + HiGHS, ~0.8 s per scenario)
- **Time resolution:** 12 slices = 4 seasons (Summer Mar–May, Monsoon Jun–Sep, Post-monsoon Oct–Nov, Winter Dec–Feb)
  × 3 periods (Day 08–16, Evening 16–22, Night 22–08). This captures solar's absence at night, monsoon cloud, the
  monsoon wind peak, monsoon hydro, and the evening peak. An annual-energy version (kept as `mix_lp_annual_v0.py`) gave
  0% coal and 74% solar, because it cannot see night-time or seasons. That result was rejected.
- **Decisions:** new capacity by region and source; 4-hour batteries (BESS) and 8-hour pumped storage (PSP);
  dispatch in each slice; storage charge/discharge (daily cycle); flows on the 7 inter-regional corridors; when the
  green-hydrogen electrolysers run.
- **Committed fleet (sunk cost, O&M only):**
  - Coal 229 GW = 221.9 GW today − 60 GW reaching 40 years by 2047 + 39.5 GW under construction + 22.9 GW contracted + 5 GW lignite.
  - Existing gas 20 GW.
  - Hydro: operating + under construction.
  - Nuclear: operating + under construction + sanctioned (22.6 GW).
  - PSP: operating + under construction (23.3 GW).
- **Limits:**
  - Resource potentials: NISE solar, NIWE 150 m wind, CEA hydro, CEA 267 GW PSP.
  - National build caps: CEA 2035-36 projection + a stretch annual build rate. Solar 1,279 GW; wind 375 GW; hydro 111 GW; nuclear ≤ 100 GW (Mission); coal ≤ 280 GW; gas ≤ 60 GW.
- **Reliability:**
  - Firm capacity ≥ peak × 1.15, using capacity credits.
  - Coal ≥ 40% minimum load relative to its evening output (CEA flexibility norm).
  - Nuclear runs flat.
- **Climate:** CO₂ ≤ 1.2 Gt (base: held at today's 1.20 Gt). The cap is soft: any overshoot is penalised at ₹20,000/t and reported. Unserved energy is penalised at ₹50/kWh and reported.
- **Assumptions:** every cost, capacity credit and cap is in `data/mix_assumptions.csv` with its basis.

## Base result, 2047

| | Coal | Gas | Nuclear | Hydro | Solar | Wind | Total |
|---|---|---|---|---|---|---|---|
| Generation (TWh) | 1,239 | 26 | 583 | 365 | 2,396 | 1,051 | **5,660** |
| Share | 21.9% | 0.5% | 10.3% | 6.5% | 42.3% | 18.6% | non-fossil **77.7%** |
| Capacity (GW) | 229 | 20 | 83 | 111 | 1,279 | 375 | + BESS 481, PSP 23 |

- **Emissions and cost:** CO₂ 1,200 Mt (cap binding; implied carbon price ₹2,630/t ≈ $30/t). Average system cost ₹3.71/kWh.
- **Coal plant load factor:** 62% (today ~64%). Coal shifts toward evening and night; daytime coal drops to minimum load.

**Regional mix (share of the region's own generation):**

| Region | Generation (TWh) | Mix | Net trade |
|---|---|---|---|
| Northern | 1,712 | solar 76%, hydro 10%, coal 10% | exports 236 TWh (Rajasthan solar) |
| Western | 1,812 | solar 43%, coal 31%, wind 22% | balanced |
| Southern | 1,544 | wind 42%, solar 21%, nuclear 20%, coal 14% | balanced |
| Eastern | 478 | coal 59%, nuclear 39% | imports ~190 TWh (weak solar resource) |
| North-Eastern | 115 | hydro 97% | exports 45 TWh |

## Verification (out/mix_verification_base.csv): 13/13 checks pass
These checks are recomputed from the solution, not taken from the solver:
- Energy balance holds in all 60 region-slices.
- No unserved energy.
- National energy accounting closes.
- Capacity factors are physically possible.
- Resource limits and build caps are respected.
- The committed fleet is retained.
- CO₂ is within the cap.
- National firm capacity is 902 GW against 854 GW required.
- Coal minimum load holds.
- Storage round-trip losses are applied.
- The H₂ load is fully served.
- Corridors stay within their limits.

## Benchmarks

| | This model (base) | CEA indicative 2047 (Down To Earth, 2026) | Draft NEP 2047 |
|---|---|---|---|
| Solar | 1,279 GW | ~1,200 GW | — |
| Wind | 375 GW | 400–450 GW | — |
| Nuclear | 83 GW | 100 GW | 100 GW |
| Storage | 504 GW | 476 GW required (CEA PSP roadmap) | — |
| Pumped storage | 23 GW (BESS cheaper) | 116 GW | — |
| Non-fossil share | 78% | — | ~2/3 |

The capacities agree closely. Our non-fossil share is higher than the draft NEP because the base holds CO₂ flat; the
**Relaxed CO₂ (1.7 Gt)** scenario gives 68%, which matches NEP. The main difference is pumped storage: at CEA's
₹6 crore/MW, 4-hour batteries are cheaper. This holds even with storage costs +50%. It is flagged as a
judgement call.

## Scenarios (out/mix_scenarios_2047.csv)

| Scenario | Coal | Gas | Nuclear | Hydro | Solar | Wind | Non-fossil | Note |
|---|---|---|---|---|---|---|---|---|
| **Base** | 21.9 | 0.5 | 10.3 | 6.5 | 42.3 | 18.6 | 77.7 | |
| Strict CO₂ 0.8 Gt | 11.6 | 8.3 | 12.4 | 6.4 | 42.6 | 18.6 | 80.0 | overshoots by 22 Mt; gas replaces coal |
| Relaxed CO₂ 1.7 Gt | 31.0 | 0.6 | 2.9 | 4.7 | 42.1 | 18.6 | 68.4 | NEP-like; no new nuclear |
| Nuclear Mission 100 GW | 22.0 | 0.3 | 12.4 | 4.8 | 42.0 | 18.6 | 77.7 | |
| Nuclear delay ≤50 GW | 19.2 | 7.0 | 6.2 | 6.5 | 42.6 | 18.6 | 73.8 | carbon price ₹8,700/t |
| Faster RE build +25% | 22.0 | 0.0 | 2.9 | 4.7 | 47.4 | 23.1 | 78.0 | cheapest, ₹3.49/kWh |
| Slower RE build −25% | 26.0 | 8.4 | 12.5 | 6.5 | 32.6 | 14.0 | 65.6 | overshoots CO₂ by 393 Mt |
| Demand P10 | 24.4 | 0.2 | 3.2 | 5.3 | 46.5 | 20.5 | 75.5 | |
| Demand P90 | 29.4 | 6.7 | 9.9 | 5.2 | 34.1 | 14.8 | 63.9 | 85 TWh unserved; CO₂ +991 Mt |
| P90 + build caps ×1.23 | 19.1 | 6.6 | 9.7 | 5.5 | 41.0 | 18.0 | 74.3 | CO₂ +311 Mt |

Transmission ×2 or ×5 and solar cost +30% leave the mix unchanged.

## What the scenarios tell us
1. **Solar and wind are limited by build speed, not cost.** They hit their build caps in every scenario, so a 30%
   solar cost rise changes nothing, while ±25% build speed moves coal by 4 points and CO₂ by ~400 Mt.
2. **Nuclear is the swing resource.** It ranges from 23 to 100 GW depending on the carbon cap and how much renewable
   capacity gets built. When nuclear is delayed, gas fills the gap and the carbon price triples.
3. **Coal plateaus but does not disappear.** The 229 GW committed fleet runs at ~60% load factor in 2047, mostly
   serving the evening and night.
4. **High demand (P90) breaks today's build pace.** Meeting P90 demand within 1.2 Gt needs ~25% faster renewable
   build *and* still overshoots CO₂. The demand risk is really a delivery-speed risk.
5. **Transmission is not binding at 3× today's corridors,** because each region largely balances itself. The East is
   the exception: it depends on imports.

## Limitations (to state openly in the deck)
- 12 representative slices, not 8,760 hours. Multi-day wind or solar lulls are covered only by the reserve margin.
- The demand and resource profile shapes are stylised assumptions, documented in the code. Hourly CEA/Grid-India
  data from 13 Nov can replace them.
- Single-year optimisation for 2047. There is no 2026→2047 investment pathway, beyond what the build caps imply.
- PSP potential split for North, East and North-East is an assumption. Battery costs are held at 2026 tender levels,
  which is conservative.
- Distributed rooftop solar is modelled as part of solar. Bio and small hydro (~2%) are not modelled separately.
