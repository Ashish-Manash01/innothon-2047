"""Regional roll-up of the demand model for ANY year (generalises the 2047-only roll-up in simulate_v1.py).

For a scenario p and FY-end year t, returns per CEA region:
  organic requirement (state sums + ISTS residual allocated by FY26 shares), EV and data-centre additions
  (EV by GSDP share in year t, data centres by announced hub shares), grid generation (x bridge), green-H2 generation.
The 2047 values reproduce out/v1_regional_2047_base.csv exactly (checked in __main__).
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_v1 as dm

REG = ["Northern", "Western", "Southern", "Eastern", "North-Eastern"]
DC_SHARE = {"MH": .41, "TN": .23, "DL": .05, "HR": .05, "UP": .04, "TG": .08, "KA": .07, "GJ": .03, "WB": .02, "AP": .02}
H2_SHARE = {"GJ": .25, "OD": .15, "TN": .15, "AP": .15, "RJ": .10, "MH": .08, "KA": .07, "WB": .05}
_e = pd.read_csv(dm.D / "state_energy_requirement.csv")
_ist = _e[(_e.fy_end_year == 2026) & _e.code.str.startswith("ISTS")]
IST_SHARE = _ist.groupby("cea_region").requirement_mu.sum() / _ist.requirement_mu.sum()
DCS = pd.Series(DC_SHARE).groupby(dm.REGION).sum()
H2S = pd.Series(H2_SHARE).groupby(dm.REGION).sum()


def regional(p, years):
    nb, st = dm.run(p, detail=True)
    st = st.copy()
    st["region"] = st.code.map(dm.REGION)
    out = []
    for t in years:
        s = st[st.fy_end == t]
        org = s[s.region.notna()].groupby("region").req_twh.sum().reindex(REG).fillna(0)
        org = org + IST_SHARE.reindex(REG).fillna(0) * s[s.code == "ISTS"].req_twh.sum()
        g = s[s.gsdp_cr.notna()].set_index("code").gsdp_cr
        evs = (g / g.sum()).groupby(dm.REGION).sum().reindex(REG).fillna(0)
        n = nb.loc[t]
        add = n.gen_ev_dc / n.bridge
        evp = n.ev_twh / (n.ev_twh + n.dc_twh)
        ev = add * evp * evs; dc = add * (1 - evp) * DCS.reindex(REG).fillna(0)
        pops = s[s.region.notna()].groupby("region").pop_k.sum().reindex(REG).fillna(0)
        heat = n.heat_twh * evs  # industrial heat follows GSDP
        cook = n.cook_twh * pops / pops.sum()  # cooking follows population
        grid = (org + ev + dc + heat + cook) * n.bridge
        h2 = n.gen_h2 * H2S.reindex(REG).fillna(0)
        for r in REG:
            out.append({"fy_end": t, "region": r, "organic_req_twh": org[r], "ev_twh": ev[r], "dc_twh": dc[r],
                        "heat_twh": heat[r], "cook_twh": cook[r], "gen_grid_twh": grid[r], "gen_h2_twh": h2[r], "gen_total_twh": grid[r] + h2[r]})
    return pd.DataFrame(out), nb


if __name__ == "__main__":
    df, nb = regional(dm.SCEN["Base"], [2026, 2030, 2035, 2040, 2047])
    ref = pd.read_csv(dm.OUT / "v1_regional_2047_base.csv", index_col=0).drop(index="India")
    chk = df[df.fy_end == 2047].set_index("region")
    diff = (chk.gen_total_twh - ref.gen_total_2047_twh.reindex(chk.index)).abs().max()
    print(df.groupby("fy_end")[["gen_grid_twh", "gen_h2_twh", "gen_total_twh"]].sum().round(0))
    print("max |diff| vs saved 2047 regional (TWh):", round(diff, 2))
    nat = nb.loc[[2026, 2030, 2035, 2040, 2047], "gen_total"].round(0)
    print("national gen_total check:", nat.to_dict())
    assert diff < 0.2
