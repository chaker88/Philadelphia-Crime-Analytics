"""Download all Philadelphia crime incidents from the city's Carto API into data/."""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://phl.carto.com/api/v2/sql"
TABLE = "incidents_part1_part2"
BATCH_SIZE = 50000
OUTPUT_CSV = Path(__file__).resolve().parents[1] / "data" / f"{TABLE}.csv"


def fetch_all_rows():
    # page through the table until the API returns no more rows
    all_rows = []
    offset = 0
    while True:
        query = f"SELECT * FROM {TABLE} LIMIT {BATCH_SIZE} OFFSET {offset}"
        response = requests.get(BASE_URL, params={"q": query})
        response.raise_for_status()
        rows = response.json().get("rows", [])
        if not rows:
            break
        all_rows.extend(rows)
        print(f"Fetched {len(all_rows)} rows so far...")
        offset += BATCH_SIZE
    return pd.DataFrame(all_rows)


def main():
    df = fetch_all_rows()
    df.info()
    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
