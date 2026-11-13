"""Region-wise electricity GENERATION history, FY2018-19 to FY2025-26 (MU = GWh).

conventional_mu : thermal + nuclear + large hydro, stations > 25 MW. CEA 18-column monthly generation report,
                  sub-report 2 'Energywise performance status - regionwise', March issue (cumulative Apr-Mar),
                  published on the National Power Portal (npp.gov.in/public-reports/cea/monthly/generation/18_col_act/<YYYY>/MAR/).
                  Each year uses the 'actual same period last year' column of the following March issue (final figures);
                  FY26 uses the March-2026 issue (provisional).
re_mu           : renewable generation excluding large hydro (solar, wind, biomass, bagasse, small hydro, others).
                  CEA Monthly RE Generation Report, March issue, state-wise table, regional sub-totals.
                  FY24-FY26 issues include large hydro in the state table; large hydro (section 9 / NPP hydro rows) is subtracted.
                  FY21 is not retrievable (report offline): regional pattern interpolated from FY20/FY22, all-India total
                  from MoP national generation minus conventional; flagged.
bhutan_mu       : imports from Bhutan (reported as a separate 'region' by CEA; counted in national generation by MoP).
"""
import numpy as np, pandas as pd
from pathlib import Path
D = Path(__file__).parent
REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
CONV = {  # fy_end: NR, WR, SR, ER, NER, Bhutan
    2019: [310467.28, 471007.23, 254197.29, 192071.38, 17186.90, 4406.62],
    2020: [305220.47, 477696.61, 249146.74, 195273.09, 17652.52, 5794.48],
    2021: [293120.85, 486055.46, 217744.98, 210320.97, 18599.88, 8765.50],
    2022: [321814.39, 475863.09, 259234.03, 236236.75, 20305.61, 7493.20],
    2023: [364315.63, 493025.58, 274951.44, 259263.05, 22614.83, 6742.40],
    2024: [363795.75, 565023.38, 290869.19, 267781.51, 21070.43, 4716.10],
    2025: [384856.83, 582982.53, 307831.25, 272147.37, 20566.02, 5484.18],
    2026: [380142.73, 551140.48, 307814.93, 270004.70, 20422.07, 7831.24],
}
RE = {
    2019: [24672.03, 38168.02, 60926.55, 2708.02, 284.49],
    2020: [27189.51, 41137.31, 67009.28, 2719.01, 281.91],
    2022: [38610.64, 51453.77, 77331.23, 3241.85, 274.81],
    2023: [58579.23, 57895.56, 83002.29, 3510.00, 565.09],
    2024: [137879.95 - 73088.83, 86065.25 - 16587.36, 107628.67 - 20308.65, 21384.56 - 17785.35, 6930.32 - 6283.74],
    2025: [151265.41 - 76489.47, 101142.20 - 19689.91, 128139.26 - 33966.57, 15001.45 - 11216.85, 8094.84 - 7271.18],
    2026: [168643.15 - 82627.22, 122596.52 - 20296.28, 160715.90 - 43443.07, 16803.98 - 12610.67, 9029.52 - 8226.54],
}
# FY21: regional pattern by geometric interpolation, scaled so the all-India total matches MoP national generation
_g = np.sqrt(np.array(RE[2020]) * np.array(RE[2022]))
_re21 = 1381855.0 - sum(CONV[2021])  # MoP FY21 national generation (MU) minus conventional incl. Bhutan
RE[2021] = list(_g * _re21 / _g.sum())
rows = []
for y in sorted(CONV):
    for i, r in enumerate(REG):
        rows.append({"fy_end_year": y, "cea_region": r, "conventional_mu": CONV[y][i], "re_mu": round(RE[y][i], 2),
                     "re_interpolated": y == 2021, "provisional": y == 2026})
df = pd.DataFrame(rows); df["generation_mu"] = df.conventional_mu + df.re_mu
bh = pd.Series({y: v[5] for y, v in CONV.items()}, name="bhutan_mu")
if __name__ == "__main__":
    df.round(2).to_csv(D / "region_generation_history.csv", index=False)
    bh.rename_axis("fy_end_year").to_csv(D / "bhutan_import_history.csv")
    nat = pd.read_csv(D / "national_history.csv").set_index("fy_end_year").generation_bu
    t = df.groupby("fy_end_year").generation_mu.sum().add(bh) / 1e3
    print(pd.DataFrame({"sum_regions_plus_bhutan_bu": t.round(1), "MoP_national_bu": nat.reindex(t.index), "diff_%": ((t / nat.reindex(t.index) - 1) * 100).round(2)}))
