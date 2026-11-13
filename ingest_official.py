"""Compare the official INNOTHON datasets (released 13 Nov) with the public-source tables we built, before swapping.

Usage: python ingest_official.py <folder with the official files>

What it does
  1. Lists every CSV/XLSX in the folder with its sheets, columns and row counts (so we see the release's shape first).
  2. For each of our reference tables, looks for an official table with matching key columns and reports, row by row,
     where the values differ by more than the tolerance (default 2%).
  3. Writes out/official_diff.csv and prints a summary. It never overwrites data/: swapping a table is a deliberate,
     reviewed edit to the matching data/build_*.py, followed by `python run_all.py`.
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent; D = ROOT / "data"; OUT = ROOT / "out"
TOL = 0.02

# our table -> (key columns, value columns) that an official table might share. Column names are matched loosely.
OURS = {
    "national_history.csv": (["fy_end_year"], ["generation_bu", "population_mn", "gdp_cr_2011_12"]),
    "region_generation_history.csv": (["cea_region", "fy_end_year"], ["generation_mu"]),
    "region_generation_fy26.csv": (["cea_region"], ["coal_lignite", "gas", "nuclear", "hydro", "solar", "wind"]),
    "region_capacity_mar26.csv": (["cea_region"], ["coal", "gas", "nuclear", "hydro"]),
    "state_master.csv": (["code"], ["pop_2026_k"]),
}
ALIASES = {"fy_end_year": ["year", "fy", "financial_year", "fy_end"], "cea_region": ["region", "grid_region"],
           "code": ["state_code", "state"], "generation_bu": ["generation", "gross_generation", "generation_twh"],
           "requirement_mu": ["energy_requirement", "requirement", "demand_mu"], "coal_lignite": ["coal"]}


def norm(c):
    return str(c).strip().lower().replace(" ", "_").replace("-", "_")


def load_release(folder):
    tables = {}
    for f in sorted(Path(folder).glob("*")):
        try:
            if f.suffix.lower() == ".csv":
                tables[f.name] = pd.read_csv(f)
            elif f.suffix.lower() in (".xlsx", ".xls"):
                for sh, df in pd.read_excel(f, sheet_name=None).items():
                    tables[f"{f.name}:{sh}"] = df
        except Exception as ex:  # report and continue: one bad file must not stop the comparison
            print(f"  could not read {f.name}: {ex}")
    for k, df in tables.items():
        df.columns = [norm(c) for c in df.columns]
        print(f"  {k}: {len(df)} rows · {list(df.columns)[:12]}")
    return tables


def find(df, col):
    for c in [col] + ALIASES.get(col, []):
        if c in df.columns:
            return c
    return None


def compare(tables):
    rows = []
    for ours, (keys, vals) in OURS.items():
        mine = pd.read_csv(D / ours)
        for name, off in tables.items():
            kmap = {k: find(off, k) for k in keys}
            if None in kmap.values():
                continue
            for v in vals:
                ov = find(off, v)
                if ov is None or v not in mine.columns:
                    continue
                m = mine[keys + [v]].merge(off[list(kmap.values()) + [ov]].rename(columns={b: a for a, b in kmap.items()} | {ov: "official"}), on=keys)
                m["rel_diff"] = (m.official.astype(float) - m[v].astype(float)) / m[v].astype(float).abs().clip(lower=1e-9)
                for _, r in m.iterrows():
                    rows.append({"our_table": ours, "official_table": name, "column": v, **{k: r[k] for k in keys},
                                 "ours": r[v], "official": r.official, "rel_diff": r.rel_diff, "flag": abs(r.rel_diff) > TOL})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print("Official release contents:")
    T = load_release(sys.argv[1])
    diff = compare(T)
    if diff.empty:
        print("\nNo official table matched our keys automatically: map columns by hand in ALIASES and rerun.")
        sys.exit(0)
    diff.to_csv(OUT / "official_diff.csv", index=False)
    s = diff.groupby(["our_table", "official_table", "column"]).agg(rows=("flag", "size"), flagged=("flag", "sum"),
                                                                    max_abs_diff=("rel_diff", lambda x: x.abs().max()))
    print("\nComparison (flag = differs by more than 2%):"); print(s.to_string())
    print(f"\nFull row-level diff: {OUT / 'official_diff.csv'}")
