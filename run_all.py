"""One command rebuilds everything, in order, and stops at the first failure.

    python run_all.py                 # rebuild from current data/
    python run_all.py --compare official/   # first diff the official release against our tables (see ingest_official.py)

Order: data tables + checks -> regional generation history -> generation-only demand model -> Monte Carlo/tornado -> demand tests -> mix scenarios
(13 checks) -> FY26 backcast -> pathway -> dashboard exports -> deck slide files.
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
STEPS = [
    ("Data tables + validation", ["data/validate_all.py"]),
    ("Official dataset cross-check", ["data/check_official_dataset.py"]),
    ("Demand model (generation basis)", ["model/demand_gen.py"]),
    ("Monte Carlo + tornado + regional", ["model/simulate.py", "2000"]),
    ("Demand model tests", ["model/test_demand.py"]),
    ("Mix scenarios + verification", ["model/run_mix.py"]),
    ("FY26 backcast", ["model/backcast_fy26.py"]),
    ("Pathway FY30-FY47", ["model/pathway.py"]),
    ("Dashboard datasets", ["model/export_dashboard.py"]),
    ("Deck slide files", ["deck/build_deck.py"]),
]

if __name__ == "__main__":
    if "--compare" in sys.argv:
        folder = sys.argv[sys.argv.index("--compare") + 1]
        subprocess.run([sys.executable, str(ROOT / "ingest_official.py"), folder], check=True)
    for name, cmd in STEPS:
        t = time.time()
        r = subprocess.run([sys.executable, str(ROOT / cmd[0])] + cmd[1:], cwd=ROOT, capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"{'OK ' if ok else 'FAIL'} {name:36s} {time.time()-t:6.1f}s")
        if not ok:
            print(r.stdout[-3000:], r.stderr[-3000:]); sys.exit(1)
    print("All steps passed. Re-upload out/dash/*.csv to the dashboard and out/../deck/project to the deck.")
