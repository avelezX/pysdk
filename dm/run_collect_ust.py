"""
Runner: Collect US Treasury yield curve (Nominal + TIPS) from treasury.gov.
Stores in xerenity.ust_yield_curve table.
Incremental load per curve_type, fetches only the current year.

Schedule: Daily at 21:00 UTC (Treasury publishes ~3pm ET)
"""

from datetime import date
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.us_treasury.USTreasuryCollector import fetch_ust_nominal, fetch_ust_tips

TABLE = 'ust_yield_curve'


def collect_curve(connection, curve_type, fetch_fn):
    print(f"\n{'='*50}")
    print(f"Collecting {curve_type}")

    last = connection.get_last_by(
        table_name=TABLE,
        column_name='fecha',
        filter_by=('curve_type', curve_type)
    )

    last_date = last[0]['fecha'] if len(last) > 0 else None
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    # Fetch current year (and previous year on first load)
    years = [date.today().year]
    if last_date is None:
        years.insert(0, date.today().year - 1)

    all_rows = []
    for year in years:
        try:
            df = fetch_fn(year)
            if not df.empty:
                all_rows.append(df)
                print(f"  Year {year}: {len(df)} data points")
        except Exception as e:
            print(f"  Year {year} error: {e}")

    if not all_rows:
        print(f"  No data from Treasury API")
        return

    import pandas as pd
    df = pd.concat(all_rows, ignore_index=True)

    if last_date:
        df = df[df['fecha'] > last_date]
        print(f"  After filtering: {len(df)} new rows")

    if df.empty:
        print(f"  Already up to date")
        return

    # Insert using one-shot for speed (PK handles duplicates)
    try:
        connection.insert_data_frame_one_shot(frame=df, table_name=TABLE)
        print(f"  Inserted {len(df)} rows")
    except Exception as e:
        # Fall back to row-by-row on conflict
        print(f"  One-shot failed ({e}), inserting row by row...")
        connection.insert_dataframe(frame=df, table_name=TABLE)
        print(f"  Inserted rows (with duplicate handling)")


def main():
    print(f"US Treasury Yield Curve Collector - {date.today()}")

    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    try:
        collect_curve(connection, "NOMINAL", fetch_ust_nominal)
        collect_curve(connection, "TIPS", fetch_ust_tips)
    finally:
        connection.close()

    print(f"\nDone!")


if __name__ == "__main__":
    main()
