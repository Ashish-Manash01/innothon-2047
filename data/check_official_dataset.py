"""Cross-check of the official INNOTHON dataset (renewable-india-dataset: state population, GSDP and installed RE
capacity, 2006-2024) against the series the model uses, aggregated to CEA regions.

Findings written to out/official_dataset_check.csv:
  * 'Year' is the start of the financial year (Year 2014 = FY2014-15).
  * GSDP matches MoSPI (2011-12 prices) through FY2019-20; from Year 2020 the values are model-imputed (the README
    says gaps were filled with XGBoost) and run 5-17% below MoSPI by FY2024-25, missing the post-COVID rebound.
  * Its 'Zone' column is not the CEA grid region (Rajasthan is 'West', MP/Chhattisgarh are 'Central', Sikkim is
    'North-East'); generation is reported by CEA region, so states are mapped to CEA regions here.
  * Installed capacity columns are NOT used: the rules forbid capacity as a basis for forecasting or comparison.
Use in the model: regional population and GSDP shares for history; MoSPI extends GSDP past FY2019-20.
"""
from pathlib import Path
import pandas as pd

D = Path(__file__).parent; OUT = D.parent / "out"
o = pd.read_csv(D / "official" / "renewable_energy_dataset.csv")
m = pd.read_csv(D / "state_master.csv")
name = {s.lower(): (c, r) for s, c, r in zip(m.state, m.code, m.cea_region)}
name.update({"andaman and nicobar islands": ("AN", "Southern"), "jammu and kashmir": ("JK", "Northern")})
o["code"] = o.State.str.lower().map(lambda s: name[s][0]); o["cea_region"] = o.State.str.lower().map(lambda s: name[s][1])
o["fy_end_year"] = o.Year + 1
g = pd.read_csv(D / "state_gsdp.csv")
j = o.merge(g, on=["code", "fy_end_year"], how="left")
reg = j.groupby(["fy_end_year", "cea_region"]).agg(official_gsdp=("GSDP (crore INR)", "sum"), mospi_gsdp=("gsdp_cr_2011_12", "sum"),
                                                   official_pop_mn=("Population", lambda x: x.sum() / 1e6)).reset_index()
reg["gsdp_diff_pct"] = (reg.official_gsdp / reg.mospi_gsdp - 1) * 100
nat = reg.groupby("fy_end_year")[["official_gsdp", "mospi_gsdp"]].sum()
nat["diff_pct"] = (nat.official_gsdp / nat.mospi_gsdp - 1) * 100
OUT.mkdir(exist_ok=True); reg.round(2).to_csv(OUT / "official_dataset_check.csv", index=False)
zone_vs_cea = pd.crosstab(o.Zone, o.cea_region)
if __name__ == "__main__":
    print("All-India GSDP, official vs MoSPI (%):\n", nat.diff_pct.loc[2016:].round(1).to_string())
    print("\nZone (official) vs CEA region (state-years):\n", zone_vs_cea.to_string())
    s = reg[reg.fy_end_year == 2020].set_index("cea_region")
    print("\nFY2019-20 regional GSDP shares, official:", (s.official_gsdp / s.official_gsdp.sum()).round(3).to_dict())
