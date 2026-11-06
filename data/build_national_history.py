"""Rebuild data/national_history.csv from verified sources (replaces the v0 hand-entered file).

- generation_bu : Ministry of Power "Power Sector at a Glance" (CEA), total generation incl. RE.
- population_mn : UN World Population Prospects 2024, medium variant, 1 July of the FY START year
                  (FY2025-26 -> July 2025). Years between UN anchor points (2010, 2015, 2020) are
                  geometrically interpolated (flagged).
- urban_pct_un  : same source; interpolated linearly between anchors.
- gdp_cr_2011_12: MoSPI GDP at constant 2011-12 prices (₹ crore), via statisticstimes (04 Sep 2026).
                  MoSPI introduced a 2022-23 base series in 2026; the 2011-12 base is kept because it is
                  the only consistent series covering FY2010-FY2026.
"""
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(__file__).parent
# FY2009-10: the source table printed 808.498 BU but also a 5.59% growth for FY2010-11; 808.498 -> 850.387
# implies 5.18%, while every later year reproduces the printed growth exactly. The source file has since been
# withdrawn, so FY10 is set to the value implied by the printed growth (850.387/1.0559) and flagged.
GEN = {2010: round(850.387 / 1.0559, 3), 2011: 850.387, 2012: 928.113, 2013: 969.506, 2014: 1020.200, 2015: 1110.392,
       2016: 1173.603, 2017: 1241.689, 2018: 1308.146, 2019: 1376.095, 2020: 1389.102, 2021: 1381.855,
       2022: 1491.859, 2023: 1624.465, 2024: 1739.091, 2025: 1829.698, 2026: 1847.913}
# UN WPP 2024 anchors (calendar year, 1 July): population (million), urban %
UN = {2010: (1243.481564, 30.9), 2015: (1328.024498, 32.5), 2020: (1402.617695, 34.1), 2021: (1414.203896, 34.4),
      2022: (1425.423212, 34.8), 2023: (1438.069596, 35.1), 2024: (1450.935791, 35.4), 2025: (1463.865525, 35.7),
      2026: (1476.625576, 36.0), 2030: (1525.138844, 37.2), 2035: (1578.694796, 38.7), 2040: (1622.580039, 40.2),
      2045: (1656.067582, 41.7), 2050: (1679.589259, 43.1)}
GDP = {2009: 7651078, 2010: 8301235, 2011: 8736329, 2012: 9213017, 2013: 9801370, 2014: 10527674,
       2015: 11369493, 2016: 12308193, 2017: 13144582, 2018: 13992914, 2019: 14534641, 2020: 13694869,
       2021: 15021846, 2022: 16164913, 2023: 17650591, 2024: 18796955, 2025: 20189918}  # key = FY start year


def un_interp(year):
    ys = sorted(UN)
    if year in UN:
        return UN[year][0], UN[year][1], False
    if year < ys[0]:  # back-extrapolate with the 2010-2015 rate (only FY2009-10 needs this)
        lo, hi = ys[0], ys[1]
        r = (UN[hi][0] / UN[lo][0]) ** (1 / (hi - lo))
        du = (UN[hi][1] - UN[lo][1]) / (hi - lo)
        return UN[lo][0] / r ** (lo - year), UN[lo][1] - du * (lo - year), True
    lo = max(y for y in ys if y < year); hi = min(y for y in ys if y > year)
    w = (year - lo) / (hi - lo)
    p = UN[lo][0] * (UN[hi][0] / UN[lo][0]) ** w
    u = UN[lo][1] + w * (UN[hi][1] - UN[lo][1])
    return p, u, True


rows = []
for fy_end, g in GEN.items():
    start = fy_end - 1
    p, u, interp = un_interp(start)
    rows.append({"fy": f"{start}-{str(fy_end)[2:]}", "fy_end_year": fy_end, "generation_bu": g,
                 "population_mn": round(p, 1), "urban_pct_un": round(u, 2), "gdp_cr_2011_12": GDP[start],
                 "real_gdp_growth_pct": round((GDP[start] / GDP[start - 1] - 1) * 100, 2) if start - 1 in GDP else np.nan,
                 "pop_interpolated": interp,
                 "gen_note": "derived from source growth column (source value 808.498 inconsistent)" if fy_end == 2010 else ""})
df = pd.DataFrame(rows)
df.to_csv(D / "national_history.csv", index=False)

# UN projection anchors for the forecast (calendar years)
proj = pd.DataFrame([{"year": y, "population_mn": round(v[0], 1), "urban_pct": v[1]} for y, v in UN.items() if y >= 2025])
p47, u47, _ = un_interp(2047)
proj = pd.concat([proj, pd.DataFrame([{"year": 2047, "population_mn": round(p47, 1), "urban_pct": round(u47, 2)}])])
proj.sort_values("year").to_csv(D / "un_wpp2024_projection.csv", index=False)

print(df.to_string(index=False))
print(f"\nUN WPP 2024 medium, 2047 (interpolated): population {p47:.1f} mn, urban {u47:.1f}%")
