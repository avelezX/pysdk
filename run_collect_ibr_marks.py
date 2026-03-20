"""
IBR Marks Collector — dedicated collector for all 10 IBR deposit rate series.

Series collected (all from suameca.banrep.gov.co):
  Nominal (feed ibr_quotes_curve for pricing):
  - IBR-ON   (id_serie=9,  suameca_id=241)
  - IBR-1N   (id_serie=11, suameca_id=242)
  - IBR-3N   (id_serie=13, suameca_id=243)
  - IBR-6N   (id_serie=15, suameca_id=16560)
  - IBR-12N  (id_serie=17, suameca_id=16562)

  Efectiva (supplementary, displayed in series module):
  - IBR-OE   (id_serie=10, suameca_id=15324)
  - IBR-1E   (id_serie=12, suameca_id=15325)
  - IBR-3E   (id_serie=14, suameca_id=15326)
  - IBR-6E   (id_serie=16, suameca_id=16561)
  - IBR-12E  (id_serie=18, suameca_id=16563)

This is the SINGLE authoritative source for IBR deposit rates.
These series have been removed from run_collect_suameca.py and run_collect_banrep_series.py
to prevent duplicate rows in banrep_series_value_v2.

Runs twice daily on weekdays (15:00 UTC and 18:00 UTC via GitHub Actions).
After writing, triggers update_ibr_loan_curves() to refresh ibr_quotes_curve.
"""

import datetime
import pandas as pd

from data_collectors.suameca.SuamecaCollector import SuamecaCollector
from db_connection.supabase.Client import SupabaseConnection

# ---------------------------------------------------------------------------
# Series definition
# ---------------------------------------------------------------------------

IBR_SERIES = [
    # Nominal (used by ibr_quotes_curve for pricing)
    {"suameca_id":   241, "internal_id":  9, "name": "IBR-ON"},
    {"suameca_id":   242, "internal_id": 11, "name": "IBR-1N"},
    {"suameca_id":   243, "internal_id": 13, "name": "IBR-3N"},
    {"suameca_id": 16560, "internal_id": 15, "name": "IBR-6N"},
    {"suameca_id": 16562, "internal_id": 17, "name": "IBR-12N"},
    # Efectiva (supplementary — displayed in series module)
    {"suameca_id": 15324, "internal_id": 10, "name": "IBR-OE"},
    {"suameca_id": 15325, "internal_id": 12, "name": "IBR-1E"},
    {"suameca_id": 15326, "internal_id": 14, "name": "IBR-3E"},
    {"suameca_id": 16561, "internal_id": 16, "name": "IBR-6E"},
    {"suameca_id": 16563, "internal_id": 18, "name": "IBR-12E"},
]

TABLE = 'banrep_series_value_v2'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

print("=" * 60)
print("IBR Marks Collector — SUAMECA")
print("=" * 60)

collector = SuamecaCollector()
connection = SupabaseConnection()
connection.sign_in_as_collector()

today = datetime.date.today()
is_business_day = today.weekday() < 5  # Mon=0 … Fri=4

# ---------------------------------------------------------------------------
# Fetch all 5 series in a single SUAMECA request
# ---------------------------------------------------------------------------

print(f"\nFetching {len(IBR_SERIES)} IBR series from SUAMECA...")
frames = collector.get_batch_series_data(IBR_SERIES)
print(f"SUAMECA returned data for {len(frames)} series.\n")

# ---------------------------------------------------------------------------
# Per-series: filter to new rows and insert
# ---------------------------------------------------------------------------

updated_count = 0

for series in IBR_SERIES:
    internal_id = series["internal_id"]
    name = series["name"]

    df = frames.get(internal_id)

    if df is None or df.empty:
        print(f"  {name}: WARNING — no data returned from SUAMECA")
        continue

    # Get the latest date already in the DB for this series
    last_rows = connection.get_last_by(
        table_name=TABLE,
        column_name='fecha',
        filter_by=(('id_serie', internal_id))
    )

    if last_rows:
        # DB may return timestamp strings like '2026-02-27T00:00:00' — normalise to 'YYYY-MM-DD'
        last_date_str = last_rows[0]['fecha'][:10]
        # filter: only rows strictly newer than the last stored date
        new_rows = df[df['fecha'] > last_date_str].copy()
    else:
        # No data yet in DB — insert everything
        last_date_str = None
        new_rows = df.copy()

    if new_rows.empty:
        print(f"  {name}: up to date (last: {last_date_str})")
    else:
        connection.insert_dataframe(frame=new_rows, table_name=TABLE)
        print(f"  {name}: {len(new_rows)} rows inserted (last was: {last_date_str})")
        updated_count += 1

# ---------------------------------------------------------------------------
# Per-series alerting: check whether today's data is present on business days
# ---------------------------------------------------------------------------

today_str = today.strftime('%Y-%m-%d')

if is_business_day:
    print(f"\nBusiness day check for {today_str}:")
    for series in IBR_SERIES:
        internal_id = series["internal_id"]
        name = series["name"]

        # Re-read the latest date from DB to check after the insert
        last_rows = connection.get_last_by(
            table_name=TABLE,
            column_name='fecha',
            filter_by=(('id_serie', internal_id))
        )

        if last_rows and last_rows[0]['fecha'][:10] >= today_str:
            print(f"  {name}: OK (last: {last_rows[0]['fecha'][:10]})")
        else:
            last_date = last_rows[0]['fecha'][:10] if last_rows else 'never'
            print(f"  {name}: WARNING — today's data missing (last: {last_date})")
else:
    print(f"\nWeekend ({today_str}) — skipping business-day check.")

# ---------------------------------------------------------------------------
# Trigger RPC to refresh ibr_quotes_curve
# ---------------------------------------------------------------------------

print("\nRefreshing ibr_quotes_curve via RPC...")
try:
    connection.supabase.rpc('update_ibr_loan_curves', {}).execute()
    print("  RPC update_ibr_loan_curves: OK")
except Exception as rpc_err:
    print(f"  RPC update_ibr_loan_curves: ERROR — {rpc_err}")

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

print(f"\n{'=' * 60}")
print(f"IBR marks collector complete. {updated_count}/{len(IBR_SERIES)} series updated.")
print(f"{'=' * 60}")
