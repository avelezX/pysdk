"""
Runner: Collect US reference rates (SOFR, EFFR, OBFR) from NY Fed Markets API.
Stores in xerenity.us_reference_rates table.
Uses incremental load per rate_type.

Schedule: Daily at 14:00 UTC (NY Fed publishes ~8am ET)
"""

import json
import requests
from datetime import date, timedelta
from src.collectors.ny_fed import fetch_sofr, fetch_effr, fetch_obfr, fetch_sofr_averages

# ── Supabase REST connection ──
SUPABASE_URL = "https://tvpehjbqxpiswkqszwwv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2cGVoamJxeHBpc3drcXN6d3d2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY0NTEzODksImV4cCI6MjAxMjAyNzM4OX0.LZW0i9HU81lCdyjAdqjwwF4hkuSVtsJsSDQh7blzozw"
COLLECTOR_BEARER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiAiY29sbGVjdG9yIiwiZXhwIjogMTg0NzI4ODUyMCwiaWF0IjogMTczNjk1NTc1MiwiaXNzIjogImh0dHBzOi8vdHZwZWhqYnF4cGlzd2txc3p3d3Yuc3VwYWJhc2UuY28iLCJlbWFpbCI6ICJzdmVsZXpzYWZmb25AZ21haWwuY29tIiwicm9sZSI6ICJjb2xsZWN0b3IifQ.5HX_n8SsXN4xPslndvyyYubdlDLFg2_uAUIwinEi-eU"

TABLE = "us_reference_rates"

db = requests.Session()
db.headers.update({
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {COLLECTOR_BEARER}',
    'Content-Type': 'application/json',
    'Accept-Profile': 'xerenity',
    'Content-Profile': 'xerenity',
    'Prefer': 'return=minimal',
})


def get_last_date(rate_type: str) -> str | None:
    """Get the last date stored for a rate type."""
    resp = db.get(
        f'{SUPABASE_URL}/rest/v1/{TABLE}?rate_type=eq.{rate_type}&select=fecha&order=fecha.desc&limit=1'
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


def collect_rate(rate_type: str, fetch_fn):
    """Collect a single rate type with incremental load."""
    print(f"\n{'='*50}")
    print(f"Collecting {rate_type}")

    last_date = get_last_date(rate_type)
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    # Determine date range for fetch
    if last_date:
        start = last_date  # NY Fed will return from this date
        end = date.today().isoformat()
    else:
        # First load: last 2 years
        start = (date.today() - timedelta(days=730)).isoformat()
        end = date.today().isoformat()

    df = fetch_fn(start, end)
    if df.empty:
        print(f"  No data from NY Fed API")
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
    # Clean None values for JSON serialization
    for row in rows:
        for k, v in row.items():
            if v is None:
                row[k] = None  # JSON null

    inserted = insert_rows(rows)
    print(f"  Inserted {inserted} rows")


def main():
    print(f"US Reference Rates Collector — {date.today()}")

    collect_rate("SOFR", fetch_sofr)
    collect_rate("EFFR", fetch_effr)
    collect_rate("OBFR", fetch_obfr)

    # SOFR averages use a different endpoint pattern
    print(f"\n{'='*50}")
    print(f"Collecting SOFR Averages (30d/90d/180d)")
    avgs = fetch_sofr_averages()
    if not avgs.empty:
        for rt in avgs['rate_type'].unique():
            subset = avgs[avgs['rate_type'] == rt]
            last = get_last_date(rt)
            if last:
                subset = subset[subset['fecha'] > last]
            if not subset.empty:
                rows = subset.to_dict(orient='records')
                inserted = insert_rows(rows)
                print(f"  {rt}: inserted {inserted} rows")
            else:
                print(f"  {rt}: up to date")
    else:
        print(f"  No SOFR averages data")

    print(f"\nDone!")


if __name__ == "__main__":
    main()
