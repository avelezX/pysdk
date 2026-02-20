"""
Runner: Collect US Treasury yield curves (Nominal + TIPS) from treasury.gov.
Stores in xerenity.ust_yield_curve table.
Uses incremental load — only inserts dates after the last stored date.

Schedule: Daily at 15:00 UTC (after Treasury publishes ~3pm ET previous day data)
"""

import json
import requests
from datetime import date
from src.collectors.us_treasury import fetch_ust_nominal, fetch_ust_tips

# ── Supabase REST connection ──
SUPABASE_URL = "https://tvpehjbqxpiswkqszwwv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2cGVoamJxeHBpc3drcXN6d3d2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY0NTEzODksImV4cCI6MjAxMjAyNzM4OX0.LZW0i9HU81lCdyjAdqjwwF4hkuSVtsJsSDQh7blzozw"
COLLECTOR_BEARER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiAiY29sbGVjdG9yIiwiZXhwIjogMTg0NzI4ODUyMCwiaWF0IjogMTczNjk1NTc1MiwiaXNzIjogImh0dHBzOi8vdHZwZWhqYnF4cGlzd2txc3p3d3Yuc3VwYWJhc2UuY28iLCJlbWFpbCI6ICJzdmVsZXpzYWZmb25AZ21haWwuY29tIiwicm9sZSI6ICJjb2xsZWN0b3IifQ.5HX_n8SsXN4xPslndvyyYubdlDLFg2_uAUIwinEi-eU"

TABLE = "ust_yield_curve"

db = requests.Session()
db.headers.update({
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {COLLECTOR_BEARER}',
    'Content-Type': 'application/json',
    'Accept-Profile': 'xerenity',
    'Content-Profile': 'xerenity',
    'Prefer': 'return=minimal',
})


def get_last_date(curve_type: str) -> str | None:
    """Get the last date stored for a curve type."""
    resp = db.get(
        f'{SUPABASE_URL}/rest/v1/{TABLE}?curve_type=eq.{curve_type}&select=fecha&order=fecha.desc&limit=1'
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


def collect_curve(curve_type: str, fetch_fn, year: int):
    """Collect a single curve type with incremental load."""
    print(f"\n{'='*50}")
    print(f"Collecting {curve_type} for {year}")

    last_date = get_last_date(curve_type)
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    df = fetch_fn(year)
    if df.empty:
        print(f"  No data from Treasury.gov")
        return

    print(f"  Fetched {len(df)} data points from API")

    # Incremental filter
    if last_date:
        df = df[df['fecha'] > last_date]
        print(f"  After filtering: {len(df)} new rows")

    if df.empty:
        print(f"  Already up to date")
        return

    rows = df.to_dict(orient='records')
    inserted = insert_rows(rows)
    print(f"  Inserted {inserted} rows")


def main():
    year = date.today().year
    print(f"US Treasury Yield Curve Collector — {date.today()}")

    collect_curve("NOMINAL", fetch_ust_nominal, year)
    collect_curve("TIPS", fetch_ust_tips, year)

    print(f"\nDone!")


if __name__ == "__main__":
    main()
