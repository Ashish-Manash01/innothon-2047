"""End-to-end test of the Streamlit dashboard with Streamlit's AppTest (no browser needed).

Runs the app at the base case, then exercises every control path and checks for exceptions and key numbers.
Usage: python tests/test_app.py
"""
import time
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
fails = []


def run(label, at):
    t = time.time(); at.run(timeout=300)
    dt = time.time() - t
    if at.exception:
        fails.append(label); print(f"FAIL {label}: {[e.message for e in at.exception]}")
    else:
        print(f"OK   {label:45s} {dt:5.1f}s")
    return at


at = AppTest.from_file(APP, default_timeout=300)
run("Initial load (base case)", at)
hdr = [m.value for m in at.markdown if "TWh** of electricity" in m.value][0]
print("     header:", hdr[:160])
assert "5,553 TWh" in hdr, "base total should be 5,553 TWh"
m = {x.label: x.value for x in at.metric}
print("     metrics:", {k: m[k] for k in list(m)[:6]})
assert m["Non-fossil share 2047"].startswith("77.6"), m["Non-fossil share 2047"]

# demand sliders
at.slider(key="gdp").set_value(7.5); run("GDP 7.5%", at)
at.slider(key="h2").set_value(25.0); run("Hydrogen 25 Mt", at)
at.select_slider(key="ev").set_value("Fast"); run("EV fast", at)
at.select_slider(key="elec").set_value("High"); run("Heat + cooking electrification high", at)
assert any(m.label == "Heat + cooking electrification" and m.value != "0 TWh" for m in at.metric)
at.slider(key="b").set_value(0.85); run("Elasticity 0.85 (high demand, stress)", at)
print("     header:", [m.value for m in at.markdown if "TWh** of electricity" in m.value][0][:120])
# mix controls (sliders without keys: find by label)
sl = {s.label: s for s in at.slider}
sl["CO₂ cap, Mt"].set_value(800); run("CO₂ cap 800 Mt", at)
[s for s in at.selectbox if s.label == "Nuclear policy"][0].set_value("Delayed (≤ 50 GW)"); run("Nuclear delayed", at)
sl = {s.label: s for s in at.slider}
sl["Solar & wind build speed"].set_value(0.7); run("Build speed 0.7", at)
print("     warnings:", [w.value[:90] for w in at.warning])
at.button[[b.label for b in at.button].index("Save this setting for comparison")].click(); run("Save scenario", at)
at.button[[b.label for b in at.button].index("Reset to base case")].click(); run("Reset demand", at)
assert "5,553 TWh" in [m.value for m in at.markdown if "TWh** of electricity" in m.value][0]
sel = [s for s in at.selectbox if s.label == "State or union territory"][0]
sel.set_value("UP"); run("Trace Uttar Pradesh", at)
at.radio[0].set_value("Growth multiple"); run("Map: growth multiple", at)
at.text_input[0].set_value("solar"); run("Search assumptions", at)
ss = [s for s in at.select_slider if s.label == "Year"][0]; ss.set_value(2030); run("Pathway year 2030", at)
print("\nAll passed" if not fails else f"\n{len(fails)} failed: {fails}")
