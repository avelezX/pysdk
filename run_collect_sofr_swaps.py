"""
Runner: Collect SOFR OIS par swap curve from Eris Futures.
Stores in xerenity.sofr_swap_curve table.
Uses incremental load — only inserts dates after the last stored date.

Schedule: Daily at 21:00 UTC (Eris publishes ~15:40 ET)
"""

import json
import os
import requests
from datetime import date, timedelta
from src.collectors.eris_sofr import fetch_sofr_curve, fetch_sofr_curve_range

# ── Supabase REST connection ──
SUPABASE_URL = os.getenv("XTY_URL")
SUPABASE_KEY = os.getenv("XTY_TOKEN")
COLLECTOR_BEARER = os.getenv("COLLECTOR_BEARER")

TABLE = "sofr_swap_curve"

db = requests.Session()
db.headers.update({
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {COLLECTOR_BEARER}',
    'Content-Type': 'application/json',
    'Accept-Profile': 'xerenity',
    'Content-Profile': 'xerenity',
    'Prefer': 'return=minimal',
})


def get_last_date() -> str | None:
    """Get the last date stored in the table."""
    resp = db.get(
        f'{SUPABASE_URL}/rest/v1/{TABLE}?select=fecha&order=fecha.desc&limit=1'
    )
    if resp.status_code == 200:
        data = resp.json()
        if data and len(data) > 0:
            return data[0]['fecha']
    return None


def insert_rows(rows: list[dict]) -> int:
    """Insert rows in batches of 200. Returns count inserted."""
    inserted = 0
    batch_size = 200
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        resp = db.post(
            f'{SUPABASE_URL}/rest/v1/{TABLE}',
            data=json.dumps(batch),
        )
        if resp.status_code in (200, 201):
            inserted += len(batch)
        elif resp.status_code == 409 or 'duplicate' in resp.text.lower():
            print(f"  Batch {i // batch_size + 1}: duplicates skipped")
        else:
            print(f"  Batch {i // batch_size + 1} error: {resp.status_code} {resp.text[:200]}")
    return inserted


def main():
    print(f"SOFR Swap Curve Collector — {date.today()}")

    last_date = get_last_date()
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    if last_date:
        # Incremental: fetch from last date to today
        start = date.fromisoformat(last_date) + timedelta(days=1)
        df = fetch_sofr_curve_range(start, date.today())
    else:
        # First load: fetch ~3 months of history from archive
        start = date.today() - timedelta(days=90)
        df = fetch_sofr_curve_range(start, date.today())

    if df.empty:
        print("  Already up to date (or no new data)")
        return

    print(f"  Fetched {len(df)} data points")
    print(f"  Dates: {df['fecha'].min()} to {df['fecha'].max()}")

    rows = df.to_dict(orient='records')
    inserted = insert_rows(rows)
    print(f"  Inserted {inserted} rows")
    print(f"\nDone!")


if __name__ == "__main__":
    main()
