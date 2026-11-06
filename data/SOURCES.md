# INNOTHON reference data — catalogue, sources and checks
Built 6 Nov 2026. Rebuild everything and re-run all checks with: `python data/validate_all.py` (16 checks, all passing).

## Tables

| File | Grain | What it holds | Source | Check vs published |
|---|---|---|---|---|
| `national_history.csv` | India × FY2010–FY2026 | Generation (BU), population, urban %, real GDP (2011-12 prices), growth | MoP *Power Sector at a Glance* (CEA); UN WPP 2024 medium; MoSPI national accounts | Generation exact; GDP growth matches MoSPI to 0.01 pp |
| `un_wpp2024_projection.csv` | India × 2025–2050 | Population & urban % projection, incl. interpolated 2047 (1,665 mn, 42.3%) | UN WPP 2024 medium variant | — |
| `state_master.csv` | 36 States/UTs | CEA grid region, INNOTHON-site region, population 2011/21/26/31/36, urban % | MoHFW Technical Group projections 2011-36 (Table 11), NIUA *Urban Statistics 2022* Table 1.2 | 2026 total 1,429.4 mn exact; 2036 +0.07% |
| `state_energy_requirement.csv` | State × FY14,15,16,18,20–26 | Electricity energy requirement (MU) + ISTS-direct residual per region | MoP Parliament replies (LS SQ 164; RS SQ 5; RS USQ 1752); CEA LGBR 2018-19, 2025-26, 2026-27 | Every year within +0.03% of All-India (gap = island grids) |
| `state_energy_fy2027_cea_forecast.csv` | State | CEA anticipated FY27 requirement | CEA LGBR 2026-27 | — |
| `state_gsdp.csv` | 33 States/UTs × FY12–FY26 | Real GSDP (₹ cr, 2011-12 prices) | MoSPI via statisticstimes (state pages + Oct-2026 table) | Sum 2024-25 = GDP +0.9% (normal) |
| `state_resources.csv` | 36 States/UTs | Wasteland & feasible wasteland (km²), solar GWp, wind 150 m GW, hydro (exploitable / operating / under construction / balance MW), coal & lignite (Mt) | NISE/MNRE 2025 solar assessment Table 5; NIWE 150 m (LS AU542); CEA hydro status 31.05.2026; MoC Annual Report 2025-26 (GSI 01.04.2025) | All four national totals exact |
| `state_re_generation_fy26.csv` | State × source | FY26 generation: solar, wind, bio, small hydro, large hydro (MU) | MNRE *RE Statistics 2025-26* Table 9.2 (source CEA) | All five source totals exact |
| `region_generation_fy26.csv` | 5 regions × 9 sources | **Current generation mix** (TWh): coal+lignite, gas, nuclear, hydro, solar, wind, bio, small hydro, Bhutan import | CEA Daily Generation Report 31-03-2026; CEA gas-station report Mar-2026; MNRE Table 9.2 | Sum 1,847.5 vs 1,847.9 TWh (−0.02%) |
| `region_capacity_mar26.csv` | 5 regions × mode | Installed capacity (MW) 31-03-2026 | CEA/NPP installed-capacity regional summary | All-India 532,740 MW |
| `nuclear_sites.csv` | 22 sites | Operating, under construction, sanctioned, in-principle sites (MW) | CEA capacity; DAE replies in Parliament (2024–Aug 2026) | Operating sum 8,780 MW exact |
| `techno_economics.csv` | 6 sources | FY26 capacity factor (derived), 2047 CF (assumed), new-build cost range (₹/kWh), CO₂ factor | Derived from this dataset; MoP reply on new-plant costs (2025); 2025 auction results; CEA CO₂ Baseline Database v20 | — |
| `generation_requirement_bridge.csv` | India × FY14–FY26 | Gross generation ÷ energy requirement (≈1.077 since FY17) | Computed from the national tables | — |

## Decisions and caveats (say these out loud in the methodology)
1. **Metric.** All outputs are *generation*. `energy requirement` is consumption-side (state periphery); it is converted to generation with the empirical bridge ratio (≈1.077, FY22–26 mean), which is expected to fall as low-auxiliary RE replaces coal.
2. **Regions.** CEA's five grid regions, because all electricity data is published that way. The INNOTHON site map puts Sikkim in the North-East (CEA: Eastern). Sikkim is <0.1% of demand. We follow CEA and note the difference.
3. **Population.** State *shares* come from the official MoHFW Technical Group projections (to 2036); the national *total* comes from UN WPP 2024 (to 2050). The Technical Group runs ~2% below UN in 2026.
4. **GDP.** MoSPI introduced a 2022-23 base in 2026. We keep the 2011-12 base for a consistent FY2010–FY2026 series. GSDP is used only for between-state shares; national GDP drives the national model.
5. **Entities.** J&K and Ladakh combined (reported jointly since FY21). DNH and Daman & Diu combined. DVC (serves Jharkhand + West Bengal) kept separate; split 50/50 only for per-capita work (assumption). FY14 undivided Andhra Pradesh excluded.
6. **ISTS residual.** From FY23, CEA regional totals include entities drawing directly from the inter-state grid (railways, large industry). These are kept as an `ISTS_<region>` row so regions reconcile exactly (largest in the West: 6–14 TWh).
7. **Mixed GSDP vintages.** Eight small states lack a same-vintage 2024-25 value; the index value is used and flagged (Goa, Sikkim, Mizoram, Nagaland show odd growth as a result).
8. **Gaps.** State requirement for FY17 and FY19 not yet located (national totals known). Wind potential for "other states" (27.14 GW) not itemised. Gas new-build cost is an estimate (no recent tariff).
9. **Errors found and corrected while building.** (a) Mixing two GSDP vintages produced fake jumps (UP +12.6%); fixed by keeping one vintage per state. (b) The all-states GSDP table's India row is one year behind its labels; national series used instead. (c) v0's population inputs were ~1% low; replaced with UN WPP 2024.
