"""Clean the raw incidents CSV and add date/time features."""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
INPUT_CSV = DATA_DIR / "incidents_part1_part2.csv"
OUTPUT_CSV = DATA_DIR / "cleaned_incidents.csv"
LOCAL_TZ = "America/New_York"
COLS = ['dispatch_date_time', 'text_general_code', 'dc_dist', 'psa',
        'point_x', 'point_y', 'location_block', 'dc_key']


def extract(path):
    return pd.read_csv(path, usecols=COLS)


def transform(df):
    df = df.copy()
    df['dispatch_date_time'] = pd.to_datetime(df['dispatch_date_time'], errors='coerce')

    # delete rows with missing data
    df = df.dropna(subset=['point_x', 'point_y', 'dispatch_date_time'])

    # dispatch_date_time is UTC (kept that way in the output); date parts use Philadelphia local time
    local = df['dispatch_date_time'].dt.tz_convert(LOCAL_TZ)

    # create new columns for year, month and time
    df['year'] = local.dt.year
    df['month'] = local.dt.month
    df['time'] = local.dt.time

    # day is 06:00-17:59, night is everything else
    hour = local.dt.hour
    df['is_day_night'] = np.where((hour >= 6) & (hour < 18), 'day', 'night')
    return df


def load(df, path):
    path.parent.mkdir(exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows to {path}")


def main():
    df = extract(INPUT_CSV)
    df = transform(df)
    df.info()
    load(df, OUTPUT_CSV)


if __name__ == "__main__":
    main()
