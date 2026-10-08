"""Data loading and figure builders for the Philadelphia crime dashboard (app.py).

The dashboard works from pre-aggregated incident counts in dashboard/data/, built by
scripts/build_dashboard_data.py. Each table counts incidents by year, crime type and one more
dimension (month, hour or district).
"""

import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# chart colors
BLUE = "#2a78d6"
ORANGE = "#eb6834"
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NIGHT_HOURS = [*range(0, 6), *range(18, 24)]  # day = 06:00-17:59


# --- data ---

def load_data():
    """Aggregated count tables keyed by their extra dimension."""
    return {
        name: pd.read_csv(os.path.join(DATA_DIR, f"by_{name}.csv"), dtype={"crime_type": "category"})
        for name in ["month", "hour", "district"]
    }


def load_districts():
    with open(os.path.join(DATA_DIR, "police_districts.geojson"), encoding="utf-8") as f:
        return json.load(f)


def load_last_date():
    with open(os.path.join(DATA_DIR, "meta.json"), encoding="utf-8") as f:
        return pd.Timestamp(json.load(f)["last_date"])


def filter_data(data, years, crime_types):
    filtered = {}
    for name, table in data.items():
        mask = table["year"].between(*years)
        if crime_types:
            mask &= table["crime_type"].isin(crime_types)
        filtered[name] = table[mask]
    return filtered


# --- KPIs ---

def kpis(data):
    """Headline numbers for the KPI tiles."""
    total = data["month"]["incidents"].sum()
    if total == 0:
        return {"Incidents": "0", "At night": "-", "Peak hour": "-", "Busiest district": "-"}
    hourly = data["hour"].groupby("hour")["incidents"].sum()
    districts = data["district"].groupby("district")["incidents"].sum()
    return {
        "Incidents": f"{total:,}",
        "At night": f"{hourly[hourly.index.isin(NIGHT_HOURS)].sum() / hourly.sum():.0%}",
        "Peak hour": f"{hourly.idxmax()}:00",
        "Busiest district": str(districts.idxmax()) if len(districts) else "-",
    }


# --- figures ---

def _style(fig, title, height=380):
    fig.update_layout(
        title={"text": title, "x": 0, "font": {"size": 15, "color": TEXT}},
        height=height,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": MUTED, "size": 12},
        hoverlabel={"bgcolor": "white", "font_color": TEXT},
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, title=None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=None)
    return fig


def _empty(title):
    fig = go.Figure()
    fig.add_annotation(text="No incidents for this selection", showarrow=False, font={"color": MUTED})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, title)


def _type_totals(table):
    return table.groupby("crime_type", observed=True)["incidents"].sum().sort_values(ascending=False)


def fig_yearly(by_month, last_date):
    title = "Incidents per year"
    if by_month.empty:
        return _empty(title)
    per_year = by_month.groupby("year")["incidents"].sum()
    fig = go.Figure(go.Scatter(
        x=per_year.index, y=per_year.values, mode="lines+markers",
        line={"color": BLUE, "width": 2}, marker={"size": 8},
        hovertemplate="%{x}: %{y:,} incidents<extra></extra>",
    ))
    # the latest year is usually incomplete; say so on the chart
    if last_date.month < 12 and per_year.index.max() == last_date.year:
        fig.add_annotation(x=last_date.year, y=per_year.iloc[-1], text=f"partial (to {last_date:%d %b})",
                           showarrow=False, yshift=-18, font={"size": 11, "color": MUTED})
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(dtick=2)
    return _style(fig, title)


def fig_top_types(by_month, n=10):
    title = f"Top {n} crime types"
    if by_month.empty:
        return _empty(title)
    totals = _type_totals(by_month)
    top = totals.head(n).sort_values()
    share = top / totals.sum()
    fig = go.Figure(go.Bar(
        x=top.values, y=top.index.astype(str), orientation="h", marker_color=BLUE,
        customdata=share.values,
        hovertemplate="%{y}: %{x:,} (%{customdata:.1%})<extra></extra>",
    ))
    return _style(fig, title)


def fig_seasonality(by_month, last_date):
    title = "Average incidents per day, by month"
    # leave out the partial latest year unless it's all that is selected
    complete = by_month["year"] < last_date.year
    full = by_month[complete] if complete.any() else by_month
    if full.empty:
        return _empty(title)
    monthly = full.groupby(["year", "month"])["incidents"].sum().reset_index()
    days = pd.to_datetime({"year": monthly["year"], "month": monthly["month"], "day": 1}).dt.days_in_month
    per_day = (monthly["incidents"] / days).groupby(monthly["month"]).mean()
    fig = go.Figure(go.Bar(
        x=[MONTHS[m - 1] for m in per_day.index], y=per_day.values, marker_color=BLUE,
        hovertemplate="%{x}: %{y:,.0f} per day<extra></extra>",
    ))
    return _style(fig, title)


def fig_hourly(by_hour):
    title = "Incidents by hour of day (local time)"
    if by_hour.empty:
        return _empty(title)
    hourly = by_hour.groupby("hour")["incidents"].sum().reindex(range(24), fill_value=0)
    share = hourly / hourly.sum()
    fig = go.Figure()
    for label, color, hours in [("Day", BLUE, list(range(6, 18))), ("Night", ORANGE, NIGHT_HOURS)]:
        fig.add_bar(
            x=hours, y=hourly[hours].values, name=label, marker_color=color,
            customdata=share[hours].values,
            hovertemplate="%{x}:00 - %{y:,} (%{customdata:.1%})<extra>" + label + "</extra>",
        )
    fig = _style(fig, title)
    fig.update_layout(showlegend=True, legend={"orientation": "h", "x": 1, "xanchor": "right", "y": 1.12},
                      bargap=0.15)
    fig.update_xaxes(dtick=2)
    return fig


def fig_night_share(by_hour, n=10):
    title = "Share of incidents at night, top crime types"
    if by_hour.empty:
        return _empty(title)
    top = by_hour[by_hour["crime_type"].isin(_type_totals(by_hour).head(n).index)]
    night = (
        top[top["hour"].isin(NIGHT_HOURS)].groupby("crime_type", observed=True)["incidents"].sum()
        .div(_type_totals(top))
        .fillna(0)
        .sort_values()
    )
    fig = go.Figure(go.Bar(
        x=night.values, y=night.index.astype(str), orientation="h", marker_color=ORANGE,
        hovertemplate="%{y}: %{x:.0%} at night<extra></extra>",
    ))
    fig.add_vline(x=0.5, line={"color": MUTED, "width": 1, "dash": "dash"})
    fig.update_xaxes(range=[0, 1], tickformat=".0%")
    return _style(fig, title)


def fig_district_map(by_district, districts):
    title = "Incidents by police district (current boundaries)"
    counts = by_district.groupby("district")["incidents"].sum().reset_index()
    if counts.empty:
        return _empty(title)
    counts["district"] = counts["district"].astype(str)  # matches the GeoJSON's dist_numc
    fig = px.choropleth_map(
        counts,
        geojson=districts,
        locations="district",
        featureidkey="properties.dist_numc",
        color="incidents",
        color_continuous_scale="Blues",
        hover_name="district",
        hover_data={"district": False, "incidents": ":,"},
        map_style="carto-positron",
        center={"lat": 40.0, "lon": -75.13},
        zoom=9.3,
        opacity=0.8,
    )
    fig = _style(fig, title, height=560)
    fig.update_layout(coloraxis_colorbar={"title": "Incidents", "thickness": 12})
    return fig
