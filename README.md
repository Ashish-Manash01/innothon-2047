# India 2047 Electricity Generation Forecast — ExxonMobil INNOTHON 2026

An interactive dashboard and the models behind it. It forecasts India's electricity **generation** in FY2046-47, nationally and for CEA's five grid regions, and recommends each region's mix across coal, hydro, solar, wind, nuclear and natural gas.

## The dashboard (`streamlit_app.py`)
Every number is computed live by the models in `model/`. Moving a slider re-runs the state demand model, the regional split, the least-cost optimiser and the 2026→2047 pathway, in about 2 seconds.

| Tab | What a reviewer can do |
|---|---|
| Overview | National forecast with uncertainty band, regional mix for 2047, state tile map, each region's role |
| Demand forecast | Change GDP, income elasticity, maturity, population, EVs, data centres, hydrogen and the generation ratio; trace any state's population, urbanisation, use per person and requirement; download all states |
| Generation mix | Change the CO₂ cap, nuclear policy, build speed, transmission, storage and solar cost; see the national and regional mix, imports/exports, supply by season and time of day, capacity, and 13 independent checks on the solution |
| Pathway to 2047 | FY26 actual and FY30 / FY35 / FY40 / FY47 solutions: generation, capacity, CO₂ against the cap, regional mix by year |
| Compare scenarios | Saved settings side by side with the base and draft-NEP-like cases; demand tornado |
| Validation | FY26 backcast, benchmarks against CEA / NEP / published studies, elasticity robustness, model tests |
| Assumptions & sources | Every parameter with its basis, resource potential vs use, data sources, AI-use disclosure |

## Run locally
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy free on Streamlit Community Cloud (about 5 minutes)
1. Create a new GitHub repository, for example `innothon-2047`, and upload the contents of this folder to it. The upload must include the `model/`, `data/`, `out/` and `.streamlit/` folders.
2. Go to share.streamlit.io and sign in with GitHub.
3. Click **Create app**, choose the repository, set branch `main` and main file `streamlit_app.py`.
4. Under **Advanced settings**, pick Python 3.13. Then click **Deploy**.
5. You get a public link, `https://<name>.streamlit.app`, to share with the jury.

## Rebuild everything
`python run_all.py` rebuilds data tables, models, checks and exports (about 2 minutes). `python tests/test_app.py` drives the dashboard through 15 interactions and fails on any error.

## Official data (13 Nov)
`python ingest_official.py <folder>` compares the released files with our tables and flags differences above 2%. Then update `data/build_*.py` and run `python run_all.py`.

AI tools: built with help from Claude (Anthropic), as the competition terms require us to disclose.
