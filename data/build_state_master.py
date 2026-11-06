"""Build data/state_master.csv: one row per State/UT with grid region, population and urbanisation.

Sources
- Population (1 July, persons): Report of the Technical Group on Population Projections 2011-2036
  (MoHFW/NCP, July 2020), Table 11, as transcribed state-by-state on statisticstimes.com (Feb 2026).
- Urban % : same report (1 March basis), as reprinted in NIUA Handbook of Urban Statistics 2022, Table 1.2.
- Grid region: CEA regional grouping (used by all CEA electricity data). The INNOTHON site map
  shows Sikkim under North-Eastern; CEA reports it under Eastern. We follow CEA for data
  consistency and flag the difference (Sikkim is <0.1% of demand).
"""
from pathlib import Path
import pandas as pd

# code, name, cea_region, pop 2011/2021/2026/2031/2036 (thousand), urban% 2011/2021/2031/2036
ROWS = [
    ("CH", "Chandigarh",        "Northern", 1061, 1212, 1270, 1321, 1362, 97.2, 99.7, 100.0, 100.0),
    ("DL", "Delhi",             "Northern", 16914, 20703, 22674, 24688, 26727, 97.5, 99.4, 100.0, 100.0),
    ("HR", "Haryana",           "Northern", 25492, 29604, 31409, 33047, 34570, 34.9, 40.9, 46.7, 49.6),
    ("HP", "Himachal Pradesh",  "Northern", 6884, 7406, 7588, 7717, 7790, 10.0, 10.3, 10.5, 10.6),
    ("JK", "Jammu & Kashmir",   "Northern", 12309, 13440, 13927, 14387, 14773, 27.5, 30.0, 32.6, 33.9),
    ("LA", "Ladakh",            "Northern", 275, 298, 306, 312, 316, 22.6, 29.6, 36.9, 40.9),
    ("PB", "Punjab",            "Northern", 27836, 30404, 31370, 32125, 32696, 37.5, 41.1, 44.8, 46.6),
    ("RJ", "Rajasthan",         "Northern", 68928, 79572, 83879, 87422, 90787, 24.9, 26.3, 27.7, 28.4),
    ("UP", "Uttar Pradesh",     "Northern", 200897, 231704, 243466, 252432, 259459, 22.3, 23.7, 25.2, 25.9),
    ("UK", "Uttarakhand",       "Northern", 10131, 11439, 12028, 12554, 13004, 30.2, 35.0, 39.6, 42.0),
    ("CG", "Chhattisgarh",      "Western", 25680, 29607, 31311, 32810, 34172, 23.2, 26.5, 29.7, 31.3),
    ("GJ", "Gujarat",           "Western", 60754, 70075, 74343, 78157, 81542, 42.6, 47.7, 52.6, 55.0),
    ("MP", "Madhya Pradesh",    "Western", 73039, 84860, 89965, 94307, 98054, 27.6, 28.8, 29.9, 30.4),
    ("MH", "Maharashtra",       "Western", 112798, 124762, 129584, 133672, 136985, 45.2, 48.0, 50.7, 52.1),
    # DNH&DD: 2026 from TG table; 2011 = census sum; 2021/31/36 ESTIMATED (merged UT not on source pages);
    # urban % = population-weighted average of DNH and D&D rows in NIUA Table 1.2
    ("DN", "Dadra & Nagar Haveli and Daman & Diu", "Western", 587, 1440, 1593, 1760, 1940, 58.6, 78.2, 86.9, 88.4),
    ("GA", "Goa",               "Western", 1462, 1561, 1601, 1635, 1665, 62.2, 73.7, 83.8, 88.2),
    ("AP", "Andhra Pradesh",    "Southern", 49697, 52849, 53740, 54180, 54257, 29.5, 35.3, 41.5, 44.7),
    ("TG", "Telangana",         "Southern", 35077, 37771, 38665, 39220, 39480, 38.9, 46.1, 53.5, 57.3),
    ("KA", "Karnataka",         "Southern", 61304, 66986, 69074, 70738, 72034, 38.7, 43.4, 48.3, 50.7),
    ("KL", "Kerala",            "Southern", 33484, 35537, 36239, 36712, 36965, 47.7, 71.0, 90.1, 96.4),
    ("TN", "Tamil Nadu",        "Southern", 72313, 76479, 77582, 78081, 78066, 48.4, 52.8, 57.3, 59.6),
    ("PY", "Puducherry",        "Southern", 1258, 1584, 1771, 1976, 2198, 68.3, 69.9, 71.3, 71.8),
    ("LD", "Lakshadweep",       "Southern", 65, 68, 70, 71, 72, 77.6, 96.8, 100.0, 100.0),
    ("BR", "Bihar",             "Eastern", 104771, 123695, 132850, 141543, 149078, 11.3, 12.1, 12.9, 13.3),
    ("JH", "Jharkhand",         "Eastern", 33176, 38637, 41108, 43339, 45285, 24.0, 25.8, 27.5, 28.4),
    ("OD", "Odisha",            "Eastern", 42107, 45793, 47221, 48311, 49077, 16.7, 18.5, 20.5, 21.5),
    ("WB", "West Bengal",       "Eastern", 91530, 98285, 100631, 102218, 102982, 31.9, 36.0, 40.2, 42.4),
    ("SK", "Sikkim",            "Eastern", 612, 678, 709, 737, 760, 25.2, 44.9, 65.2, 74.6),
    ("AN", "Andaman & Nicobar Islands", "Eastern", 381, 401, 406, 411, 413, 37.6, 43.0, 48.7, 51.6),
    ("AR", "Arunachal Pradesh", "North-Eastern", 1388, 1537, 1608, 1671, 1722, 22.9, 25.2, 27.5, 28.6),
    ("AS", "Assam",             "North-Eastern", 31336, 35155, 36815, 38276, 39479, 14.1, 15.3, 16.5, 17.2),
    ("MN", "Manipur",           "North-Eastern", 2864, 3172, 3318, 3449, 3553, 29.2, 31.9, 34.6, 35.9),
    ("ML", "Meghalaya",         "North-Eastern", 2975, 3295, 3447, 3583, 3692, 20.1, 20.6, 21.0, 21.3),
    ("MZ", "Mizoram",           "North-Eastern", 1100, 1219, 1275, 1325, 1365, 52.1, 54.5, 56.9, 58.0),
    ("NL", "Nagaland",          "North-Eastern", 1984, 2198, 2299, 2389, 2462, 28.9, 42.9, 57.3, 64.3),
    ("TR", "Tripura",           "North-Eastern", 3684, 4081, 4268, 4437, 4571, 26.2, 37.0, 48.2, 53.9),
]
cols = ["code", "state", "cea_region", "pop_2011_k", "pop_2021_k", "pop_2026_k", "pop_2031_k", "pop_2036_k",
        "urban_2011_pct", "urban_2021_pct", "urban_2031_pct", "urban_2036_pct"]
df = pd.DataFrame(ROWS, columns=cols)
df["urban_2026_pct"] = ((df.urban_2021_pct + df.urban_2031_pct) / 2).round(1)  # linear interpolation
df["innothon_site_region"] = df.cea_region.where(df.code != "SK", "North-Eastern")
df["estimated_flag"] = df.code.eq("DN").map({True: "pop 2021/31/36 estimated", False: ""})
df.to_csv(Path(__file__).with_name("state_master.csv"), index=False)

# ---- checks
tot = df[[c for c in cols if c.startswith("pop_")]].sum()
print("Population totals (million):", (tot / 1e3).round(1).to_dict())
print("Published: 2011 Census 1,210.9; TG 2021 ~1,363; TG 2026 1,429.4 (statisticstimes); TG 2036 1,522.3")
for y in ["2011", "2036"]:
    u = (df[f"pop_{y}_k"] * df[f"urban_{y}_pct"]).sum() / df[f"pop_{y}_k"].sum()
    print(f"Pop-weighted urban % {y}: {u:.1f}  (NIUA India row: {'31.1' if y=='2011' else '39.6'})")
print(df.groupby("cea_region")[["pop_2026_k", "pop_2036_k"]].sum().div(1e3).round(1))
