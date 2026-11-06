"""Build data/state_energy_requirement.csv (long format) — state-wise electricity ENERGY REQUIREMENT (MU).

Energy requirement = demand at state periphery (unrestricted, includes unmet demand). It is a
CONSUMPTION-side quantity; the national model converts to GENERATION by adding T&D/aux losses.
We use requirement (not 'supplied') so that pre-2019 shortage years don't understate demand.

Sources (fy_end -> source)
- 2014, 2015, 2016 : MoP, Lok Sabha Starred Q.164 (28.07.2016), Annex-I
- 2018             : CEA LGBR 2018-19, Annexure-II (actual 2017-18)
- 2020             : MoP, Rajya Sabha Starred Q.5, Annex (actual 2019-20)
- 2021-2024        : MoP, Rajya Sabha Unstarred Q.1752/1744 (Aug 2025), Annexure-III
- 2025             : CEA LGBR 2025-26, Annex-II (actual 2024-25; Mar-25 provisional)
- 2026             : CEA LGBR 2026-27, Annex-II (actual 2025-26)
- 2027 (forecast)  : CEA LGBR 2026-27, anticipated 2026-27 (kept in separate column, not history)
Gaps: FY2016-17 and FY2018-19 state tables not located yet (national totals known).

Entity handling
- J&K and Ladakh reported jointly from FY21 -> entity 'JK' covers J&K + Ladakh in all years.
- Daman & Diu + Dadra & Nagar Haveli summed -> 'DN'.
- DVC (Damodar Valley Corp., serves parts of Jharkhand and West Bengal) kept as its own entity;
  for per-capita work it is split 50/50 JH/WB (assumption, flagged). Region totals unaffected.
- FY14 Andhra Pradesh is undivided AP (Telangana formed June 2014) -> FY14 AP/TG set to NaN;
  FY15 AP includes Apr-May 2014 of undivided state (flagged).
"""
from pathlib import Path
import numpy as np
import pandas as pd

YEARS = [2014, 2015, 2016, 2018, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
N = np.nan
D = {  # code: [FY14, FY15, FY16, FY18, FY20, FY21, FY22, FY23, FY24, FY25, FY26], FY27 anticipated
    "CH": ([1574, 1616, 1607, 1610, 1732, 1523, 1606, 1788, 1789, 1952, 1879], 2119),
    "DL": ([26867, 29231, 29626, 31825, 33086, 29560, 31128, 35143, 35501, 38253, 38556], 39799),
    "HR": ([43463, 46615, 47506, 50775, 54505, 53161, 55499, 61451, 63983, 70149, 70493], 73369),
    "HP": ([9089, 8807, 8821, 9399, 10424, 10186, 12115, 12649, 12805, 13533, 13642], 14804),
    "JK": ([15613, 16214, 16572, 18809, 20025, 19773, 19957, 19639, 20040, 20374, 20185], 23110),
    "PB": ([47821, 48629, 49687, 54812, 56776, 58445, 62846, 69522, 69533, 77470, 75409], 84584),
    "RJ": ([58202, 65717, 67417, 71193, 81281, 85311, 89814, 101801, 107422, 113840, 110657], 130475),
    "UP": ([94890, 103179, 106351, 120051, 122549, 124367, 129448, 144251, 148791, 164978, 163501], 169945),
    "UK": ([11944, 12445, 12889, 13457, 14472, 13827, 15521, 15647, 15644, 16773, 16538], 18562),
    "CG": ([18932, 21499, 25649, 25915, 30111, 30472, 31908, 37446, 39930, 43174, 42933], 51132),
    "GJ": ([88497, 96235, 103544, 109985, 113940, 111622, 123953, 139043, 145768, 152228, 156588], 172312),
    "MP": ([49410, 53374, 62374, 69926, 76172, 83437, 86501, 92683, 99301, 104398, 103711], 117732),
    "MH": ([126288, 134897, 141817, 149760, 155167, 150679, 172823, 187309, 207108, 202855, 202867], 238152),
    "DN": ([2252 + 5390, 2086 + 5307, 2337 + 5925, 2534 + 6167, 2574 + 6528, 2223 + 5497, 9433, 10018, 10164, 10851, 11182], 11737),
    "GA": ([3890, 3969, 5120, 4117, 4350, 4083, 4448, 4669, 5111, 5408, 5449], 5943),
    "AP": ([N, 59198, 50436, 58384, 65452, 62080, 68413, 72302, 80209, 79041, 81204], 91350),
    "TG": ([N, 43337, 50254, 60318, 68306, 66998, 70539, 77832, 84623, 88384, 87274], 107537),
    "KA": ([64150, 62643, 64302, 67869, 72799, 68851, 72437, 75688, 94088, 92550, 95791], 101297),
    "KL": ([21577, 22459, 23318, 25004, 26315, 25118, 26579, 27747, 30943, 31617, 31157], 33641),
    "TN": ([93508, 95758, 97276, 106006, 108816, 101194, 109816, 114798, 126163, 130187, 132328], 143876),
    "PY": ([2344, 2402, 2437, 2669, 2847, 2644, 2894, 3051, 3456, 3552, 3508], 3929),
    "LD": ([48, 48, 48, 48, 46, 56, 56, 64, 64, 68, 73], N),
    "BR": ([15391, 19294, 23961, 27019, 31627, 34171, 36216, 39545, 41514, 44471, 47440], 50746),
    "DVC": ([17407, 18222, 18437, 21550, 22429, 21368, 23741, 26339, 26560, 25885, 24755], 29248),
    "JH": ([7143, 7599, 7735, 7906, 8941, 9953, 11148, 13278, 14408, 15194, 15435], 15728),
    "OD": ([24958, 26482, 26762, 28801, 29692, 29848, 38339, 42631, 41358, 42786, 44199], 52337),
    "WB": ([42891, 47086, 47359, 50760, 52948, 51644, 54001, 60348, 67576, 71172, 72970], 76480),
    "SK": ([413, 399, 399, 486, 554, 546, 610, 587, 544, 569, 554], 683),
    "AN": ([240, 240, 240, 330, 346, 346, 335, 348, 386, 421, 423], N),
    "AR": ([552, 677, 626, 799, 753, 719, 875, 915, 1014, 1050, 1194], 1326),
    "AS": ([7544, 8527, 8762, 9095, 9804, 10192, 10844, 11465, 12445, 12843, 13616], 15602),
    "MN": ([579, 705, 840, 872, 924, 974, 1019, 1014, 1023, 1073, 1178], 1345),
    "ML": ([1794, 1930, 1833, 1555, 2112, 2031, 2256, 2237, 2236, 2046, 2095], 2801),
    "MZ": ([446, 455, 471, 497, 647, 728, 656, 645, 684, 714, 754], 1136),
    "NL": ([577, 688, 755, 795, 814, 826, 852, 926, 921, 938, 996], 1107),
    "TR": ([1195, 1242, 1202, 2600, 1538, 1484, 1578, 1547, 1691, 1888, 1903], 2134),
}
# Published All-India requirement (MU) for the check
ALL_INDIA = {2014: 1002257, 2015: 1068923, 2016: 1114408, 2018: 1213325, 2020: 1291010, 2021: 1275534,
             2022: 1379812, 2023: 1513497, 2024: 1626132, 2025: 1695188, 2026: 1707493}

master = pd.read_csv(Path(__file__).with_name("state_master.csv"))
region = dict(zip(master.code, master.cea_region)) | {"DVC": "Eastern"}
rows = [{"code": c, "cea_region": region[c], "fy_end_year": y, "requirement_mu": v}
        for c, (vals, _) in D.items() for y, v in zip(YEARS, vals)]
df = pd.DataFrame(rows)

# Published REGION totals (MU) from the same sources. From FY23 CEA regional totals include
# "other miscellaneous entities drawing power directly from ISTS" (e.g. railways). Add the residual
# as an 'ISTS_<region>' entity so regions reconcile exactly with CEA.
REGION_TOTALS = {
    2023: {"Northern": 463088, "Western": 477393, "Southern": 371467, "Eastern": 182791, "North-Eastern": 18758},
    2024: {"Northern": 476852, "Western": 517714, "Southern": 419531, "Eastern": 192013, "North-Eastern": 20022},
    2025: {"Northern": 518908, "Western": 530207, "Southern": 425377, "Eastern": 200134, "North-Eastern": 20561},
    2026: {"Northern": 512458, "Western": 536483, "Southern": 431311, "Eastern": 205417, "North-Eastern": 21825},
}
STANDALONE = {"LD", "AN"}  # not part of regional totals
extra = []
for y, regs in REGION_TOTALS.items():
    s = df[(df.fy_end_year == y) & ~df.code.isin(STANDALONE)].groupby("cea_region").requirement_mu.sum()
    for r, tot in regs.items():
        abbr = {"Northern": "NR", "Western": "WR", "Southern": "SR", "Eastern": "ER", "North-Eastern": "NER"}[r]
        extra.append({"code": f"ISTS_{abbr}", "cea_region": r, "fy_end_year": y,
                      "requirement_mu": tot - s[r]})
df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
df["flag"] = ""
df.loc[df.code.str.startswith("ISTS_"), "flag"] = "residual: entities drawing directly from ISTS (CEA note ##)"
df.loc[(df.code == "AP") & (df.fy_end_year == 2015), "flag"] = "includes Apr-May 2014 undivided AP"
df.loc[df.code == "JK", "flag"] = "J&K + Ladakh combined"
# Outliers found in the verification scan (values are official; flags tell the model how to treat them)
df.loc[(df.code == "TR") & (df.fy_end_year == 2018), "flag"] = "EXCLUDE: includes export to Bangladesh (CEA note)"
df.loc[(df.code == "OD") & (df.fy_end_year >= 2022), "flag"] = "step change +28% in FY22: possible reporting/coverage change"
df.loc[(df.code == "KA") & (df.fy_end_year == 2024), "flag"] = "drought year: agricultural pumping surge"
df.to_csv(Path(__file__).with_name("state_energy_requirement.csv"), index=False)
pd.DataFrame({"code": list(D), "anticipated_fy2027_mu": [v[1] for v in D.values()]}
             ).to_csv(Path(__file__).with_name("state_energy_fy2027_cea_forecast.csv"), index=False)

# ---- checks
chk = df.groupby("fy_end_year").requirement_mu.sum().to_frame("sum_states")
chk["published_all_india"] = pd.Series(ALL_INDIA)
chk["gap_pct"] = ((chk.sum_states / chk.published_all_india - 1) * 100).round(2)
print(chk)
print("\nRegion totals (TWh):")
print((df.pivot_table(index="cea_region", columns="fy_end_year", values="requirement_mu", aggfunc="sum") / 1e3).round(0))
