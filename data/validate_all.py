"""Rebuild every reference table and run all reconciliation checks. Usage: python data/validate_all.py

Each check compares our assembled table against an independently published total.
Exit code 1 if any check fails its tolerance.
"""
import subprocess, sys
from pathlib import Path
import pandas as pd

D = Path(__file__).parent
BUILDERS = ["build_national_history.py", "build_state_master.py", "build_region_generation_history.py",
            "build_state_gsdp.py", "build_resources.py", "build_techno_economics.py"]
for b in BUILDERS:
    subprocess.run([sys.executable, str(D / b)], check=True, capture_output=True)

r = lambda f: pd.read_csv(D / f)
nat, sm, gs = r("national_history.csv"), r("state_master.csv"), r("state_gsdp.csv")
rgh = r("region_generation_history.csv")
res, reg, reg_g = r("state_resources.csv"), r("state_re_generation_fy26.csv"), r("region_generation_fy26.csv")

checks = []  # (name, ours, published, tolerance_pct)
checks.append(("Population 2026, sum of states (TG, thousand)", sm.pop_2026_k.sum(), 1429404, 0.1))
checks.append(("Population 2036, sum of states (TG, thousand)", sm.pop_2036_k.sum(), 1522300, 0.2))
bh = r("bhutan_import_history.csv").set_index("fy_end_year").bhutan_mu
for y in (2019, 2022, 2024, 2026):
    s = (rgh[rgh.fy_end_year == y].generation_mu.sum() + bh[y]) / 1e3
    checks.append((f"Regional generation FY{y} + Bhutan vs national (BU)", s, nat.set_index("fy_end_year").generation_bu[y], 0.1))
g25 = gs[gs.fy_end_year == 2025].gsdp_cr_2011_12.sum()
checks.append(("GSDP 2024-25 sum vs GDP (states normally exceed by 0-3%)", g25, 18796955, 3.0))
checks.append(("Solar potential (GWp)", res.solar_potential_gwp.sum(), 3343.37, 0.01))
checks.append(("Feasible wasteland (km2)", res.feasible_wasteland_km2.sum(), 27571.39, 0.01))
checks.append(("Hydro exploitable (MW)", res.hydro_exploitable_mw.sum(), 133410, 0.01))
checks.append(("Coal resources (Mt)", res.coal_resource_mt.sum(), 400715.45, 0.01))
checks.append(("Solar generation FY26 (MU)", reg.solar.sum(), 174756.51, 0.01))
checks.append(("Wind generation FY26 (MU)", reg.wind.sum(), 106699.80, 0.01))
checks.append(("Regional generation FY26 total (TWh)", reg_g.total.sum(), 1847.913, 0.1))
checks.append(("National generation FY26 (BU)", nat.set_index("fy_end_year").generation_bu[2026], 1847.913, 0.0))

ok = True
print(f"{'check':62s} {'ours':>14s} {'published':>14s} {'diff%':>8s}")
for name, ours, pub, tol in checks:
    d = (ours / pub - 1) * 100
    flag = "OK" if abs(d) <= tol else "FAIL"
    ok &= flag == "OK"
    print(f"{name:62s} {ours:14,.2f} {pub:14,.2f} {d:+8.3f} {flag}")
print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)
