# Demand model v1 — results and method (6 Nov 2026)

"2047" = FY2046-47. All figures are electricity **generated** (TWh). FY26 actual: 1,847.9 TWh.

## Headline (FY2046-47)
| | Low | **Base** | High | Monte Carlo P10 | **P50** | P90 |
|---|---|---|---|---|---|---|
| Grid demand (organic + EV + data centres) | 3,560 | **4,966** | 7,919 | 4,565 | **5,202** | 6,087 |
| + Green hydrogen | 229 | 588 | 1,326 | 434 | 676 | 981 |
| **Total generation requirement** | 3,789 | **5,553** | 9,245 | 5,217 | **5,912** | 6,828 |

- Base growth: 4.8% a year (grid only) / 5.4% a year (total). Low and High combine every low or every high assumption at once, so they are outer bounds, not probabilities. **Use P10–P90 as the uncertainty band.**
- Published 2047 scenarios (5,254–6,033 TWh) sit inside our P10–P50. The screening answer (5,400 TWh) is within the band.
- Base is below P50 because the uncertainties are right-skewed: EVs, hydrogen and income elasticity have more room to surprise upward.

## Composition, Base 2047 (TWh generated)
Organic demand 4,248 · EVs + data centres 718 · green hydrogen 588 = 5,553.

## Method
1. **State panel** (32 states × 11 years, 332 observations, R² 0.986): log kWh per person = state effect + 0.689 × log real income per person (cluster-robust SE 0.075) + urbanisation + COVID dummy. Stable across robustness checks (0.66–0.69).
2. **Urbanisation finding:** across states, +1 pp urban share goes with +2.2% demand per person on its own, but it is fully explained by income (correlation 0.71). Within states, the independent effect ≈ 0. Urbanisation is kept explicitly in the equation, with its uncertainty, and its channel is explained.
3. **ML cross-check:** gradient boosting had 16.3% out-of-sample error (FY24–26) vs 9.2% for the regression and 8.8% for carrying the last value forward. The interpretable model is kept; short-horizon error is dominated by weather years.
4. **Projection:** population = UN WPP 2024 total × MoHFW state shares. Income = national GDP growth (5.5 / 6.5 / 7.5%) × state shares with damped historical drift. Elasticity declines linearly to k × b by 2047 (k = 0.75 base) as demand matures.
5. **Base year** = weather-smoothed FY26 (fitted + mean residual FY24–26). FY26 demand grew only +0.7% against +7.4% GDP, so the base is +4.2% above actual. Check: model FY27 = 1,859 TWh vs CEA's own FY27 forecast of 1,887 TWh (−1.5%).
6. **New loads** (not visible in history; the part already embedded in the trend is subtracted):
   - EVs: bottom-up fleet model (2W, cars, 3W, buses, trucks), 459 TWh in 2047. Calibrated to pass 27 TWh in FY31 and 38 TWh in FY32 (IEA ~25 in 2030; IESA ~38 in FY32).
   - Data centres: Wood Mackenzie path, 10 TWh (2025) → 191 TWh (2040) → 250 TWh (2047).
   - Green H₂: 12 Mt × 48 kWh/kg (NGHM 5 Mt by 2030 needs ~257 TWh; NITI–RMI 29 Mt by 2050). Kept as a separate layer.
7. **Requirement → generation:** bridge 1.077 (FY22–26 mean) falling to 1.06 by 2047 as low-auxiliary renewables replace coal. Hydrogen ×1.02 (captive supply).
8. **Uncertainty:** 2,000-run Monte Carlo. Biggest swing factors: green H₂ (1,096 TWh span), income elasticity (1,060), GDP growth (997), EV fleet (839).

## Regional, Base 2047 (TWh generated)
| Region | Grid | + H₂ | Total | × FY26 |
|---|---|---|---|---|
| Western | 1,613 | 194 | 1,807 | 3.0 |
| Southern | 1,317 | 217 | 1,535 | 3.2 |
| Northern | 1,417 | 59 | 1,475 | 2.6 |
| Eastern | 549 | 118 | 667 | 2.9 |
| North-Eastern | 70 | 0 | 70 | 2.9 |
| **India** | **4,966** | **588** | **5,553** | **2.9** |

These are **requirements** (where electricity is used). Where it should be **generated** is the job of the mix model, which comes next. Data-centre and H₂ locations follow today's hubs (DC: Mumbai 41%, Chennai 23%, NCR 14%) and announced green-hydrogen/port clusters; both are flagged assumptions.

## Open items for v2
- Replace the FY26 base with the official datasets after 13 Nov.
- Electrification of industry and cooking beyond the income trend (currently assumed captured by the elasticity).
- Validate EV fleet stock assumptions against a published 2047 fleet study.
