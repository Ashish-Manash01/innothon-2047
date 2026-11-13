"""Regional roll-up of the generation-only demand model (demand_gen.py) for any year.

For a scenario p and FY-end year t, returns per CEA region (all TWh GENERATED):
  organic production requirement (region model), new loads allocated to regions (EVs and heat by GSDP share,
  cooking by population, data centres by announced hub shares, green H2 by announced hub shares), grid total, H2.
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import demand_gen as dm

REG = dm.REG
DC_SHARE = {"MH": .41, "TN": .23, "DL": .05, "HR": .05, "UP": .04, "TG": .08, "KA": .07, "GJ": .03, "WB": .02, "AP": .02}
H2_SHARE = {"GJ": .25, "OD": .15, "TN": .15, "AP": .15, "RJ": .10, "MH": .08, "KA": .07, "WB": .05}
DCS = pd.Series(DC_SHARE).groupby(dm.REGION).sum().reindex(REG).fillna(0)
H2S = pd.Series(H2_SHARE).groupby(dm.REGION).sum().reindex(REG).fillna(0)


def regional(p, years):
    nb, st = dm.run(p, detail=True)
    out = []
    for t in years:
        s = st[st.fy_end == t].set_index("region").reindex(REG)
        n = nb.loc[t]
        gs = s.gsdp_index / s.gsdp_index.sum(); ps = s.pop_k / s.pop_k.sum()
        add = n.gen_ev_dc
        evp = n.ev_twh / (n.ev_twh + n.dc_twh)
        ev = add * evp * gs; dc = add * (1 - evp) * DCS
        heat = n.heat_twh * n.bridge * gs; cook = n.cook_twh * n.bridge * ps
        grid = s.organic_twh + ev + dc + heat + cook
        h2 = n.gen_h2 * H2S
        for r in REG:
            out.append({"fy_end": t, "region": r, "organic_twh": s.organic_twh[r], "ev_twh": ev[r], "dc_twh": dc[r],
                        "heat_twh": heat[r], "cook_twh": cook[r], "gen_grid_twh": grid[r], "gen_h2_twh": h2[r],
                        "gen_total_twh": grid[r] + h2[r], "pop_mn": s.pop_k[r] / 1e3})
    return pd.DataFrame(out), nb


if __name__ == "__main__":
    df, nb = regional(dm.SCEN["Base"], [2026, 2030, 2035, 2040, 2047])
    tot = df.groupby("fy_end").gen_total_twh.sum()
    print(df[df.fy_end == 2047].set_index("region")[["organic_twh", "ev_twh", "dc_twh", "gen_grid_twh", "gen_h2_twh", "gen_total_twh"]].round(0))
    diff = (tot - nb.loc[tot.index, "gen_total"]).abs().max()
    print("regions sum to national (max |diff| TWh):", round(diff, 3)); assert diff < 0.5
