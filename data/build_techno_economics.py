"""Build data/techno_economics.csv and data/generation_requirement_bridge.csv.

1) Capacity factors: DERIVED from our own FY26 data (generation / average installed capacity), so they are
   consistent with the dataset rather than borrowed from literature. 2047 values are stated assumptions.
2) Costs: Ministry of Power reply in Parliament (2025) for NEW plants (Rs/kWh) + 2025 auction evidence.
   Gas has no recent new-build tariff: estimated from fuel cost (formula below), flagged.
3) Emission factors (tCO2/MWh, combustion, net): CEA CO2 Baseline Database v20 (grid avg 0.727 FY24;
   operating margin ~0.96, dominated by coal). Coal 0.96 (CEA OM proxy), lignite 1.20, gas CCGT 0.40
   (IPCC 2006 default natural gas 56.1 tCO2/TJ at ~50% efficiency) -> flagged as assumptions.
4) Bridge: gross generation / energy requirement, by year, from our own national series. Needed to convert
   any consumption-side quantity into GENERATION (the metric the challenge requires).
"""
from pathlib import Path
import pandas as pd

D = Path(__file__).parent
H = 8.76  # thousand hours/year -> GW * H = TWh at 100%

# ---- FY26 implied capacity factors (avg of Mar-25 and Mar-26 capacity, GW)
cap_mar25 = {"coal_lignite": 221.8 + 6.6, "gas": 24.5, "nuclear": 8.18, "hydro": 46.9 + 4.7, "solar": 105.6, "wind": 50.0}
cap_mar26 = {"coal_lignite": 221.94 + 6.62, "gas": 20.12, "nuclear": 8.78, "hydro": 51.41, "solar": 150.26, "wind": 56.09}
gen_fy26 = {"coal_lignite": 1306.84 - 26.03, "gas": 26.03, "nuclear": 55.16, "hydro": 167.16, "solar": 174.76, "wind": 106.70}
cf = {k: gen_fy26[k] / (((cap_mar25[k] + cap_mar26[k]) / 2) * H) for k in gen_fy26}

rows = [
 # source, cf_fy26 (derived), cf_2047_assumed, lcoe_new_low, lcoe_new_high, co2_t_per_mwh, firm, notes
 ("coal",    cf["coal_lignite"], 0.55, 5.0, 6.3, 0.96, True,
  "MoP: new coal Rs5-6/kWh; 2025 TBCB tariffs Rs5.38-6.30. 2047 CF falls as coal shifts to flexible/backup role."),
 ("gas",     cf["gas"],          0.20, 7.0, 10.0, 0.40, True,
  "No recent new-build tariff. Estimate: CCGT heat rate ~7.95 MJ/kWh x LNG $10-12/MMBtu ~ Rs6.5-7.5 fuel + fixed cost at low PLF. Peaking/balancing role."),
 ("nuclear", cf["nuclear"],      0.80, 6.0, 7.0, 0.0, True,
  "MoP: new nuclear Rs6-7/kWh. PHWR-700 fleet; 80% CF achievable (Kakrapar/Rawatbhata history)."),
 ("hydro",   cf["hydro"],        0.38, 5.0, 6.0, 0.0, True,
  "MoP: new hydro Rs5-6/kWh. CF depends on monsoon; FY26 was a strong hydro year."),
 ("solar",   cf["solar"],        0.21, 2.5, 3.0, 0.0, False,
  "MoP: new solar Rs2.5-3.0/kWh. 2047 CF assumes trackers/bifacial (utility plants 20-24%). Solar+4h BESS auctions Rs2.9-3.5 (2025)."),
 ("wind",    cf["wind"],         0.30, 3.0, 4.0, 0.0, False,
  "MoP: new wind Rs3-4/kWh. NIWE 150 m potential counts only sites with CUF >25%; hub-height repowering raises fleet CF."),
]
te = pd.DataFrame(rows, columns=["source", "cf_fy26_derived", "cf_2047_assumed", "lcoe_new_low_rs_kwh",
                                 "lcoe_new_high_rs_kwh", "co2_t_per_mwh", "firm_dispatchable", "notes"])
te["cf_fy26_derived"] = te.cf_fy26_derived.round(3)
te.to_csv(D / "techno_economics.csv", index=False)

# ---- Bridge: gross generation (TWh) / energy requirement (TWh)
nat = pd.read_csv(D / "national_history.csv").set_index("fy_end_year")
REQ = {2014: 1002.257, 2015: 1068.923, 2016: 1114.408, 2017: 1142.928, 2018: 1213.326, 2019: 1274.595,
       2020: 1291.010, 2021: 1275.534, 2022: 1379.812, 2023: 1513.497, 2024: 1626.132, 2025: 1695.188,
       2026: 1707.493}
br = pd.DataFrame({"generation_twh": nat.generation_bu, "requirement_twh": pd.Series(REQ)}).dropna()
br["gen_over_req"] = (br.generation_twh / br.requirement_twh).round(4)
br.to_csv(D / "generation_requirement_bridge.csv")

print("FY26 derived capacity factors:", {k: round(v, 3) for k, v in cf.items()})
print("Check: coal+gas+nuclear+hydro+solar+wind FY26 =", round(sum(gen_fy26.values()), 1), "TWh (+bio 17.1, SHP 12.0, Bhutan 7.8)")
print("\nGeneration / requirement ratio:\n", br.gen_over_req.to_string())
print("Mean FY22-FY26:", round(br.loc[2022:2026, "gen_over_req"].mean(), 4))
