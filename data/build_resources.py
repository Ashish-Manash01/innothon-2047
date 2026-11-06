"""Build resource & current-mix reference tables.

Outputs
  data/state_resources.csv        solar/land, wind, hydro, coal/lignite potential by state
  data/state_re_generation_fy26.csv  RE generation by state & source, FY2025-26 (MU)
  data/region_generation_fy26.csv    generation by region x source, FY2025-26 (TWh)  <- current mix
  data/region_capacity_mar26.csv     installed capacity by region x mode (MW), 31-03-2026
  data/nuclear_sites.csv             operating / under-implementation / approved nuclear sites

Sources
- Solar & land : NISE/MNRE "Solar PV Potential Assessment of India (Ground Mounted)", Sep 2025, Table 5
                 (total & feasible wasteland km2, potential GWp; <=10% of a state's wasteland used).
- Wind         : NIWE 150 m agl assessment (CUF >25%), Lok Sabha AU542; 8 windy states listed, 27.14 GW
                 in "other states" not itemised.
- Hydro        : CEA "Status of large hydro electric potential development", as on 31.05.2026 (>25 MW,
                 excl. pumped storage). Reassessment 2017-23 exploitable potential 133,410 MW.
- Coal/lignite : Ministry of Coal Annual Report 2025-26 ch.2, GSI inventory as on 01.04.2025 (provisional).
- RE gen FY26  : MNRE "Renewable Energy Statistics 2025-26", Table 9.2 (source: CEA), MU.
- Conv. gen    : CEA Daily Generation Report Sub-Report-1, 31-Mar-2026 (Apr-1 to date actual, >25 MW
                 stations; thermal, nuclear, hydro by region; Bhutan import).
- Gas gen      : CEA monthly report 17 (gas/liquid stations), Apr-2025 to Mar-2026, by region.
- Capacity     : CEA/NPP installed capacity regional summary as on 31-03-2026.
- Nuclear      : CEA capacity (8,780 MW) + DAE replies in Parliament (Jan & Aug 2026).
"""
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(__file__).parent
N = np.nan
master = pd.read_csv(D / "state_master.csv")
REG = dict(zip(master.code, master.cea_region))

# ------------------------------------------------------------------ state resources
# code: (total_wasteland_km2, feasible_wasteland_km2, solar_gwp, wind150_gw, hydro_exploitable_mw,
#        hydro_operating_mw, hydro_uc_mw, hydro_balance_mw, coal_mt, lignite_mt)
R = {
 "AN": (165.90, 3.94, 0.59, N, 0, 0, 0, 0, 0, 0),
 "AP": (21814.27, 2181.43, 299.31, 123.33, 2596.0, 1610.0, 1190.0, 26.0, 4171.76, 0),
 "AR": (7810.66, 4.53, 0.47, N, 50394.0, 2115.0, 5006.0, 10389.0, 90.70, 0),
 "AS": (3556.68, 176.18, 19.17, N, 643.0, 346.0, 120.0, 143.0, 525.01, 0),
 "BR": (2995.76, 299.58, 32.99, N, 130.1, 0.0, 0.0, 0.0, 9353.44, 0),
 "CH": (2.37, 0.24, 0.02, N, 0, 0, 0, 0, 0, 0),
 "CG": (11765.16, 1032.67, 126.48, N, 1311.0, 120.0, 0.0, 1191.0, 85263.22, 0),
 "DN": (38.36, 3.84, 0.50, N, 0, 0, 0, 0, 0, 0),
 "DL": (55.15, 5.51, 0.55, N, 0, 0, 0, 0, 0, 0),
 "GA": (483.78, 48.38, 6.75, N, 0.0, 0.0, 0.0, 0.0, 0, 0),
 "GJ": (20324.34, 2032.43, 243.22, 180.79, 550.0, 550.0, 0.0, 0.0, 0, 2722.05),
 "HR": (643.31, 64.33, 6.47, N, 0.0, 0.0, 0.0, 0.0, 0, 0),
 "HP": (18510.10, 235.79, 21.50, N, 18305.0, 11471.02, 1256.0, 4259.0, 0, 0),
 "JK": (15525.87, 101.12, 8.59, N, 12264.5, 3360.0, 3551.5, 1088.0, 0, 27.55),
 "JH": (4472.70, 447.27, 51.83, N, 300.0, 210.0, 0.0, 90.0, 93254.06, 0),
 "KA": (15604.19, 1560.42, 223.28, 169.25, 4414.4, 3689.2, 0.0, 747.0, 0, 0),
 "KL": (816.17, 81.62, 12.40, N, 2472.75, 2008.15, 40.0, 419.0, 0, 9.65),
 "LA": (72860.36, 100.73, 8.56, N, 707.0, 89.0, 0.0, 618.0, 0, 0),
 "MP": (28040.69, 2730.10, 318.97, 55.42, 2819.0, 2235.0, 0.0, 584.0, 33563.62, 0),
 "MH": (37870.67, 3787.07, 486.68, 173.86, 3144.0, 2647.0, 0.0, 497.0, 13586.70, 0),
 "MN": (3091.48, 20.04, 2.29, N, 615.0, 105.0, 0.0, 510.0, 0, 0),
 "ML": (3079.51, 131.21, 14.67, N, 2026.0, 322.0, 0.0, 1488.0, 583.22, 0),
 "MZ": (1259.34, 5.15, 0.61, N, 1926.7, 60.0, 0.0, 1866.7, 0, 0),
 "NL": (835.24, 1.74, 0.19, N, 325.0, 75.0, 0.0, 64.0, 510.21, 0),
 "OD": (16442.52, 1108.22, 139.47, N, 2824.5, 2154.55, 0.0, 677.0, 100975.78, 5.93),
 "PY": (19.38, 1.38, 0.20, N, 0, 0, 0, 0, 0, 416.61),
 "PB": (960.68, 96.07, 9.21, N, 1300.73, 1096.30, 206.0, 0.0, 0, 0),
 "RJ": (77207.01, 7692.79, 828.78, 284.25, 411.0, 412.5, 0.0, 0.0, 0, 6661.17),
 "SK": (2597.73, 2.40, 0.25, N, 6051.0, 2282.0, 620.0, 2629.0, 101.23, 0),
 "TN": (13577.11, 1357.71, 204.77, 95.10, 1785.2, 1803.2, 0.0, 0.0, 0, 37523.65),
 "TG": (10235.84, 1023.58, 140.45, 54.71, 1302.0, 800.0, 0.0, 240.0, 23288.62, 0),
 "TR": (1447.62, 77.72, 9.11, N, 0.0, 0.0, 0.0, 0.0, 0, 0),
 "UP": (9153.25, 915.33, 97.84, N, 501.6, 501.6, 0.0, 0.0, 1061.80, 0),
 "UK": (7139.07, 45.28, 4.44, N, 13481.35, 4035.35, 1264.0, 3988.0, 0, 0),
 "WB": (2056.10, 195.59, 22.74, N, 809.2, 441.2, 120.0, 196.0, 34386.09, 3.93),
 "LD": (N, N, N, N, 0, 0, 0, 0, 0, 0),
}
cols = ["total_wasteland_km2", "feasible_wasteland_km2", "solar_potential_gwp", "wind150_potential_gw",
        "hydro_exploitable_mw", "hydro_operating_mw", "hydro_under_constr_mw", "hydro_balance_mw",
        "coal_resource_mt", "lignite_resource_mt"]
res = pd.DataFrame.from_dict(R, orient="index", columns=cols).rename_axis("code").reset_index()
res.insert(1, "cea_region", res.code.map(REG))
res.to_csv(D / "state_resources.csv", index=False)

# ------------------------------------------------------------------ RE generation FY26 by state (MU)
# code: (small_hydro, wind, bio, solar, large_hydro)
G = {
 "AP": (438.46, 8902.94, 486.13, 8773.06, 6190.06), "AR": (0.34, 0, 0, 2.37, 4854.46),
 "AS": (139.39, 0, 0.59, 330.12, 1424.54), "BR": (23.44, 0, 81.50, 327.71, 0),
 "CG": (244.97, 0, 1469.91, 1913.17, 351.61), "GA": (0, 0, 8.14, 57.11, 0),
 "GJ": (196.59, 33706.20, 175.56, 27379.65, 6372.91), "HR": (239.74, 0, 528.39, 1612.32, 0),
 "HP": (2693.75, 0, 0, 201.53, 42827.62), "JK": (413.60, 0, 0, 0, 15663.32),
 "JH": (19.29, 0, 0, 17.64, 145.61), "KA": (2800.48, 18804.62, 3414.10, 17923.81, 15601.21),
 "KL": (952.97, 130.33, 97.37, 2420.50, 9187.59), "LA": (0, 0, 0, 0, 465.24),
 "MP": (514.87, 4706.66, 195.57, 8076.98, 8088.74), "MH": (934.52, 8610.62, 3524.08, 10552.84, 5483.02),
 "MN": (0, 0, 0, 8.60, 576.01), "ML": (159.90, 0, 0, 0, 879.22), "MZ": (25.51, 0, 0, 29.31, 263.98),
 "NL": (97.90, 0, 0, 0, 228.33), "OD": (620.05, 0, 86.53, 909.33, 7253.62),
 "PB": (447.23, 0, 929.69, 1361.90, 4291.63), "RJ": (6.52, 7345.17, 777.10, 59921.18, 1070.61),
 "SK": (12.35, 0, 0, 0, 2602.18), "TN": (307.56, 24200.81, 194.01, 19690.99, 5589.67),
 "TG": (85.62, 292.46, 423.76, 6920.53, 6874.54), "TR": (0, 0, 0, 8.97, 0),
 "UP": (87.55, 0, 2505.77, 5302.73, 1775.64), "UK": (353.40, 0, 248.52, 331.80, 16533.16),
 "WB": (184.40, 0, 1461.93, 418.49, 2609.26), "AN": (13.72, 0, 0, 16.92, 0), "CH": (0, 0, 0, 7.94, 0),
 "DN": (0, 0, 12.64, 20.18, 0), "DL": (0, 0, 493.58, 206.53, 0), "LD": (0, 0, 0, 0.09, 0),
 "PY": (0, 0, 0, 12.24, 0),
}
re_ = pd.DataFrame.from_dict(G, orient="index", columns=["small_hydro", "wind", "bio", "solar", "large_hydro"])
re_ = re_.rename_axis("code").reset_index()
re_.insert(1, "cea_region", re_.code.map(REG))
re_.to_csv(D / "state_re_generation_fy26.csv", index=False)
RE_TOTAL_PUBLISHED = {"small_hydro": 12014.12, "wind": 106699.80, "bio": 17114.85, "solar": 174756.51,
                      "large_hydro": 167203.78}

# ------------------------------------------------------------------ conventional by region FY26 (MU)
CONV = {  # region: (thermal, nuclear, hydro)  -- CEA DGR 31-03-2026
 "Northern": (283931.04, 13565.33, 82670.29), "Western": (510617.59, 20169.21, 20284.02),
 "Southern": (242844.68, 21429.49, 43440.79), "Eastern": (257257.05, 0.0, 12537.68),
 "North-Eastern": (12186.39, 0.0, 8223.50),
}
GAS = {"Northern": 5239.50, "Western": 10412.99, "Southern": 2473.21, "Eastern": 0.0, "North-Eastern": 7900.66}
BHUTAN_IMPORT_MU = 7804.03  # arrives in Eastern region grid
re_reg = re_.groupby("cea_region")[["solar", "wind", "bio", "small_hydro"]].sum()
rows = []
for r, (th, nu, hy) in CONV.items():
    rows.append({"cea_region": r, "coal_lignite": th - GAS[r], "gas": GAS[r], "nuclear": nu, "hydro": hy,
                 "solar": re_reg.loc[r, "solar"], "wind": re_reg.loc[r, "wind"],
                 "bio": re_reg.loc[r, "bio"], "small_hydro": re_reg.loc[r, "small_hydro"],
                 "bhutan_import": BHUTAN_IMPORT_MU if r == "Eastern" else 0.0})
gen = pd.DataFrame(rows).set_index("cea_region") / 1e3  # TWh
gen["total"] = gen.sum(axis=1)
gen.round(2).to_csv(D / "region_generation_fy26.csv")

# ------------------------------------------------------------------ capacity Mar-2026 (MW)
cap = pd.DataFrame({
 "coal": [50269.00, 83271.01, 46605.00, 41045.00, 750.00], "lignite": [1580, 1400, 3640, 0, 0],
 "gas": [5711.96, 9399.39, 3346.11, 0, 1664.95], "diesel": [0, 0, 460.49, 92.71, 36.00],
 "nuclear": [2220, 3240, 3320, 0, 0], "hydro": [21665.76, 7392.00, 13596.15, 5987.75, 2773.00],
 "res_mnre": [61999.60, 86495.30, 70857.24, 2890.16, 1031.13]},
 index=["Northern", "Western", "Southern", "Eastern", "North-Eastern"]).rename_axis("cea_region")
cap.to_csv(D / "region_capacity_mar26.csv")

# ------------------------------------------------------------------ nuclear sites
NUC = [  # state, site, status, mw
 ("MH", "Tarapur (TAPS 1-4)", "operating", 1400), ("RJ", "Rawatbhata (RAPS 2-6, RAPP-7)", "operating", 1780),
 ("UP", "Narora (NAPS 1-2)", "operating", 440), ("GJ", "Kakrapar (KAPS 1-2, KAPP 3-4)", "operating", 1840),
 ("KA", "Kaiga (KGS 1-4)", "operating", 880), ("TN", "Kalpakkam (MAPS 1-2)", "operating", 440),
 ("TN", "Kudankulam (KKNPP 1-2)", "operating", 2000),
 ("RJ", "Rawatbhata RAPP-8", "under construction", 700), ("TN", "Kudankulam KKNPP 3-4", "under construction", 2000),
 ("TN", "Kudankulam KKNPP 5-6", "under construction", 2000), ("TN", "Kalpakkam PFBR", "under construction", 500),
 ("HR", "Gorakhpur GHAVP 1-2", "under construction", 1400),
 ("KA", "Kaiga 5-6", "sanctioned (pre-project)", 1400), ("HR", "Gorakhpur GHAVP 3-4", "sanctioned (pre-project)", 1400),
 ("MP", "Chutka 1-2", "sanctioned (pre-project)", 1400), ("RJ", "Mahi Banswara 1-4", "sanctioned (pre-project)", 2800),
 ("TN", "Kalpakkam FBR 1-2", "sanctioned (pre-project)", 1000),
 ("MH", "Jaitapur 1-6", "in-principle site", 9900), ("AP", "Kovvada 1-6", "in-principle site", 7248),
 ("GJ", "Chhaya Mithi Virdi 1-6", "in-principle site", 6000), ("WB", "Haripur 1-6", "in-principle site", 6000),
 ("MP", "Bhimpur 1-4", "in-principle site", 2800),
]
nuc = pd.DataFrame(NUC, columns=["code", "site", "status", "capacity_mw"])
nuc.insert(1, "cea_region", nuc.code.map(REG))
nuc.to_csv(D / "nuclear_sites.csv", index=False)

# ================================================================== checks
print("Solar potential total (GWp):", round(res.solar_potential_gwp.sum(), 2), "| published 3343.37")
print("Feasible wasteland (km2):", round(res.feasible_wasteland_km2.sum(), 2), "| published 27,571.39")
print("Wind 150m itemised (GW):", round(res.wind150_potential_gw.sum(), 2), "| published 1136.71 (+27.14 other)")
print("Hydro exploitable (MW):", round(res.hydro_exploitable_mw.sum(), 1), "| published 133,410")
print("Coal resource (Mt):", round(res.coal_resource_mt.sum(), 2), "| published 400,715.45")
print("RE FY26 by source vs published (MU):")
for k, v in RE_TOTAL_PUBLISHED.items():
    print(f"  {k:12s} {re_[k].sum():12.2f} vs {v:12.2f}")
print("Large hydro RE-table vs DGR hydro (MU):", round(re_.large_hydro.sum(), 2), "vs",
      round(sum(v[2] for v in CONV.values()), 2))
print("\nRegional generation FY26 (TWh):\n", gen.round(1))
tot = gen.total.sum()
print(f"\nNational total {tot:.1f} TWh vs MoP published 1,847.9 TWh ({(tot/1847.913-1)*100:+.2f}%)")
print("Nuclear operating sum (MW):", nuc.query("status=='operating'").capacity_mw.sum(), "| CEA 8,780")
print("\nCurrent mix share by region (%):\n", (gen.div(gen.total, axis=0) * 100).drop(columns="total").round(1))
