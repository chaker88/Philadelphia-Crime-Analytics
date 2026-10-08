"""Philadelphia crime incidents dashboard.

Local:       uv run python dashboard/app.py   then open http://127.0.0.1:8050
Production:  gunicorn dashboard.app:server
"""

import os
import sys

from dash import Dash, Input, Output, dcc, html

# make plots.py importable however the app is started (python, gunicorn, from any directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plots  # noqa: E402

# --- data (loaded once at startup) ---
data = plots.load_data()
districts = plots.load_districts()
last_date = plots.load_last_date()
min_year, max_year = int(data["month"]["year"].min()), int(data["month"]["year"].max())
crime_types = (  # most common first
    data["month"].groupby("crime_type", observed=True)["incidents"].sum()
    .sort_values(ascending=False).index.astype(str).tolist()
)

# key findings from the EDA notebook (all years, all crime types)
INSIGHTS = [
    "Recorded crime fell 38% from 2006 to the 2021 low, then partly rebounded in 2022-23.",
    "Motor vehicle theft (+167%) and thefts (+72%) rose sharply while narcotics, DUI and "
    "disorderly conduct fell over 80% (2006-08 vs 2023-25).",
    "About 20% more incidents per day in summer (Jun-Aug) than in winter (Dec-Feb).",
    "Incidents peak at 4-5 pm and bottom out at 4-6 am; gun crimes and DUI peak late at night.",
    "Crime concentrates in Center City and North Philadelphia / Kensington (districts 9, 15, 24, 22).",
]

# --- styles ---
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
PAGE = {"fontFamily": FONT, "backgroundColor": "#f3f2ee", "color": plots.TEXT,
        "padding": "24px", "maxWidth": "1400px", "margin": "0 auto"}
CARD = {"backgroundColor": plots.SURFACE, "borderRadius": "8px", "padding": "12px",
        "boxShadow": "0 1px 2px rgba(0,0,0,0.08)"}
ROW = {"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(min(420px, 100%), 1fr))",
       "gap": "16px", "marginBottom": "16px"}
LABEL = {"fontSize": "12px", "color": plots.MUTED, "marginBottom": "6px"}


def graph(graph_id):
    return html.Div(dcc.Graph(id=graph_id, config={"displayModeBar": False}), style=CARD)


def kpi_id(name):
    return "kpi-" + name.lower().replace(" ", "-")


def kpi_tile(name):
    return html.Div([
        html.Div(name, style=LABEL),
        html.Div(id=kpi_id(name), style={"fontSize": "28px", "fontWeight": 600}),
    ], style=CARD)


KPI_NAMES = ["Incidents", "At night", "Peak hour", "Busiest district"]

# --- layout ---
app = Dash(__name__, title="Philadelphia Crime")
server = app.server  # WSGI entry point for gunicorn (Render)
app.layout = html.Div([
    html.H1("Philadelphia Crime Incidents", style={"margin": "0 0 4px", "fontSize": "26px"}),
    html.Div(f"Police incidents {min_year} to {last_date:%d %b %Y}, local time.",
             style={"color": plots.MUTED, "marginBottom": "20px"}),

    # filters
    html.Div([
        html.Div([
            html.Div("Years", style=LABEL),
            dcc.RangeSlider(id="years", min=min_year, max=max_year, step=1, value=[min_year, max_year],
                            marks={y: str(y) for y in range(min_year, max_year + 1, 2)}),
        ], style={**CARD, "flex": "2"}),
        html.Div([
            html.Div("Crime types (empty = all)", style=LABEL),
            dcc.Dropdown(id="crime-types", options=crime_types, multi=True, placeholder="All crime types"),
        ], style={**CARD, "flex": "1"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "16px", "flexWrap": "wrap"}),

    # KPI tiles
    html.Div([kpi_tile(name) for name in KPI_NAMES],
             style={**ROW, "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))"}),

    # charts
    html.Div([graph("yearly"), graph("seasonality")], style=ROW),
    html.Div([graph("hourly"), graph("night-share")], style=ROW),
    html.Div([
        graph("district-map"),
        html.Div([
            html.Div(dcc.Graph(id="top-types", config={"displayModeBar": False}), style=CARD),
            html.Div([
                html.H3("Key insights (all data)", style={"margin": "0 0 8px", "fontSize": "15px"}),
                html.Ul([html.Li(text, style={"marginBottom": "6px"}) for text in INSIGHTS],
                        style={"margin": 0, "paddingLeft": "18px", "fontSize": "13px"}),
            ], style={**CARD, "marginTop": "16px"}),
        ]),
    ], style=ROW),
], style=PAGE)


# --- callback: redraw everything when a filter changes ---
@app.callback(
    [Output(kpi_id(name), "children") for name in KPI_NAMES]
    + [Output(graph_id, "figure") for graph_id in
       ["yearly", "seasonality", "hourly", "night-share", "district-map", "top-types"]],
    Input("years", "value"),
    Input("crime-types", "value"),
)
def update(years, selected_types):
    selected = plots.filter_data(data, years, selected_types)
    values = plots.kpis(selected)
    return [values[name] for name in KPI_NAMES] + [
        plots.fig_yearly(selected["month"], last_date),
        plots.fig_seasonality(selected["month"], last_date),
        plots.fig_hourly(selected["hour"]),
        plots.fig_night_share(selected["hour"]),
        plots.fig_district_map(selected["district"], districts),
        plots.fig_top_types(selected["month"]),
    ]


if __name__ == "__main__":
    app.run(debug=False)
