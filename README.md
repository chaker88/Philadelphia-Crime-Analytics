# Philadelphia Crime Analytics

An end-to-end analysis of ~3.5 million Philadelphia Police Department crime incidents (2006 to present):
a small ETL pipeline, an exploratory data analysis notebook, and an interactive Dash dashboard.

**Live dashboard: [philadelphia-crime-dashboard.onrender.com](https://philadelphia-crime-dashboard.onrender.com/)**
(hosted on Render's free plan, so the first load after a period of inactivity can take about a minute)

## Project structure

```
Philadelphia-Crime-Analytics/
├── scripts/
│   ├── download_data.py          # download all incidents from the city's Carto API
│   ├── clean_data.py             # select columns, drop incomplete rows, add date/time features
│   └── build_dashboard_data.py   # aggregate incidents into the small files the dashboard reads
├── notebooks/
│   └── eda.ipynb                 # exploratory analysis with charts and written insights
├── dashboard/
│   ├── app.py                    # Dash app: layout, filters and callback
│   ├── plots.py                  # data loading, KPIs and one function per chart
│   └── data/                     # pre-aggregated counts + district boundaries (~1.5 MB, committed)
├── data/                         # raw and cleaned CSVs, generated locally, not committed
├── requirements.txt              # runtime dependencies for deployment
├── render.yaml                   # Render deployment config
├── pyproject.toml
└── uv.lock
```

## Data

- **Crime incidents**: [OpenDataPhilly - Crime Incidents](https://opendataphilly.org/datasets/crime-incidents/),
  table `incidents_part1_part2`, fetched through the city's Carto SQL API.
- **Police district boundaries**: [OpenDataPhilly - Police Districts](https://opendataphilly.org/datasets/police-districts/),
  downloaded by `scripts/build_dashboard_data.py`.

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

Run the steps in order from the project root:

```bash
# 1. download the raw data (~900 MB) -> data/incidents_part1_part2.csv
uv run python scripts/download_data.py

# 2. clean it -> data/cleaned_incidents.csv
uv run python scripts/clean_data.py

# 3. explore: open notebooks/eda.ipynb and run all cells (kernel: the project's .venv)

# 4. rebuild the dashboard's aggregated data -> dashboard/data/
uv run python scripts/build_dashboard_data.py

# 5. launch the dashboard, then open http://127.0.0.1:8050
uv run python dashboard/app.py
```

The dashboard only reads the pre-aggregated files in `dashboard/data/` (counts by year and crime type, plus
month, hour or police district), so it starts in a few seconds and runs with little memory. These files are
committed, so the dashboard works from a fresh clone without steps 1-4; re-run them to refresh the data.

## Deployment (Render)

The dashboard is deployed at <https://philadelphia-crime-dashboard.onrender.com/> from the `main` branch using the
[Render Blueprint](https://render.com/docs/blueprint-spec) in `render.yaml`. Every merge into `main` redeploys it.

To deploy your own copy: in Render, choose **New > Blueprint**, select the repository and the `main` branch.
Render reads `render.yaml` and creates the service with these settings:

| Setting | Value |
|---|---|
| Runtime | Python 3 (`PYTHON_VERSION=3.13.9`) |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn dashboard.app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

On the free plan the service sleeps after inactivity, so the first visit after a while takes some extra time to load.

## Dashboard

[Open the live dashboard](https://philadelphia-crime-dashboard.onrender.com/)

- Filters for year range and crime types
- KPI tiles: total incidents, share at night, peak hour, busiest district
- Charts: yearly trend, seasonality (incidents per day by month), hour of day (day vs night),
  night share by crime type, top crime types, and a choropleth map of incidents by police district

## Key findings

- Recorded crime fell **38%** from 2006 (217.8k) to the 2021 low (134.3k), then partly rebounded in 2022-23.
- The mix shifted: **motor vehicle theft +167%** and **thefts +72%**, while narcotics, DUI and disorderly
  conduct fell more than 80% (2006-08 vs 2023-25 averages).
- About **20% more incidents per day in summer** than in winter.
- Incidents peak at **4-5 pm** and are lowest at 4-6 am; gun crimes and DUI peak late at night.
- Crime is concentrated in **Center City and North Philadelphia / Kensington** (districts 9, 15, 24, 22).

## Notes on the data

- `dispatch_date_time` is in UTC; all time-based analysis converts it to Philadelphia local time.
- Times are **dispatch** times, not when the crime occurred (e.g. vehicle thefts peak at 8 am, when they're discovered).
- Police districts 4, 6, 23 and 92 were merged into neighbouring districts; the map assigns incidents to
  **current** district boundaries using their coordinates.
- Most homicides are stamped exactly 00:00, so their times are not usable for time-of-day analysis.
