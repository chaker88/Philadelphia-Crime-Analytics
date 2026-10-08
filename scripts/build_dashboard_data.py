"""Pre-aggregate the cleaned incidents into the small files the dashboard reads.

The cleaned CSV is ~480 MB, too big to commit or to load on a small server, so the dashboard
works from counts instead. Every chart and filter only needs incidents counted by year and
crime type plus one other dimension (month, hour or district).

Outputs (in dashboard/data/, committed to the repo):
    by_month.csv              year, month, crime_type, incidents
    by_hour.csv               year, hour, crime_type, incidents
    by_district.csv           year, district, crime_type, incidents
    police_districts.geojson  current police district boundaries
    meta.json                 date of the latest incident
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from matplotlib.path import Path as Polygon

ROOT = Path(__file__).resolve().parents[1]
CLEANED_CSV = ROOT / "data" / "cleaned_incidents.csv"
OUT_DIR = ROOT / "dashboard" / "data"
DISTRICTS_URL = "https://opendata.arcgis.com/datasets/62ec63afb8824a15953399b1fa819df2_0.geojson"
LOCAL_TZ = "America/New_York"


def download_districts():
    return requests.get(DISTRICTS_URL, timeout=60).json()


def assign_districts(x, y, districts):
    """Current police district each point falls in (-1 = none).

    Districts 4, 6, 23 and 92 in dc_dist no longer exist, so points are mapped to today's boundaries.
    """
    xy = np.column_stack([x, y])
    result = np.full(len(xy), -1, dtype=np.int16)
    for feature in districts["features"]:
        geom = feature["geometry"]
        # a district can be one polygon or several (MultiPolygon); handle both the same way
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for polygon in polygons:
            inside = Polygon(polygon[0]).contains_points(xy)  # outer ring
            result[inside] = int(feature["properties"]["dist_numc"])
    return result


def load_incidents(districts):
    df = pd.read_csv(
        CLEANED_CSV,
        usecols=["dispatch_date_time", "text_general_code", "point_x", "point_y"],
        parse_dates=["dispatch_date_time"],
    )
    # timestamps are UTC; date parts must come from Philadelphia local time
    local = df["dispatch_date_time"].dt.tz_convert(LOCAL_TZ)
    return pd.DataFrame({
        "local_time": local,
        "year": local.dt.year,
        "month": local.dt.month,
        "hour": local.dt.hour,
        "crime_type": df["text_general_code"],
        "district": assign_districts(df["point_x"].to_numpy(), df["point_y"].to_numpy(), districts),
    })


def count_by(df, column):
    return df.groupby(["year", column, "crime_type"]).size().rename("incidents").reset_index()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    districts = download_districts()
    df = load_incidents(districts)
    print(f"Loaded {len(df):,} incidents")

    count_by(df, "month").to_csv(OUT_DIR / "by_month.csv", index=False)
    count_by(df, "hour").to_csv(OUT_DIR / "by_hour.csv", index=False)
    # incidents outside every district polygon (-1) are left off the map
    count_by(df[df["district"] != -1], "district").to_csv(OUT_DIR / "by_district.csv", index=False)

    with open(OUT_DIR / "police_districts.geojson", "w", encoding="utf-8") as f:
        json.dump(districts, f)
    with open(OUT_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"last_date": df["local_time"].max().isoformat()}, f)

    for path in sorted(OUT_DIR.iterdir()):
        print(f"{path.name}: {path.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
