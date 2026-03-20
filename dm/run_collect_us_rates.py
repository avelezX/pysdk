"""
Runner: Collect US reference rates (SOFR, EFFR, OBFR) from NY Fed Markets API.
Stores in xerenity.us_reference_rates table.
Uses incremental load per rate_type.

Schedule: Daily at 14:00 UTC (NY Fed publishes ~8am ET)
"""

from datetime import date, timedelta
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.ny_fed.NYFedCollector import (
    fetch_sofr, fetch_effr, fetch_obfr, fetch_sofr_averages
)

TABLE = 'us_reference_rates'


def collect_rate(connection, rate_type, fetch_fn):
    print(f"\n{'='*50}")
    print(f"Collecting {rate_type}")

    last = connection.get_last_by(
        table_name=TABLE,
        column_name='fecha',
        filter_by=('rate_type', rate_type)
    )

    last_date = last[0]['fecha'] if len(last) > 0 else None
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    if last_date:
        start = last_date
        end = date.today().isoformat()
    else:
        start = (date.today() - timedelta(days=730)).isoformat()
        end = date.today().isoformat()

    df = fetch_fn(start, end)
    if df.empty:
        print(f"  No data from NY Fed API")
        return

    print(f"  Fetched {len(df)} data points from API")

    if last_date:
        df = df[df['fecha'] > last_date]
        print(f"  After filtering: {len(df)} new rows")

    if df.empty:
        print(f"  Already up to date")
        return

    # Clean None values for Supabase
    df = df.where(df.notna(), None)

    try:
        connection.insert_data_frame_one_shot(frame=df, table_name=TABLE)
        print(f"  Inserted {len(df)} rows")
    except Exception as e:
        print(f"  One-shot failed ({e}), inserting row by row...")
        connection.insert_dataframe(frame=df, table_name=TABLE)
        print(f"  Inserted rows (with duplicate handling)")


def main():
    print(f"US Reference Rates Collector - {date.today()}")

    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    try:
        collect_rate(connection, "SOFR", fetch_sofr)
        collect_rate(connection, "EFFR", fetch_effr)
        collect_rate(connection, "OBFR", fetch_obfr)

        # SOFR averages (latest only, no date range)
        print(f"\n{'='*50}")
        print(f"Collecting SOFR Averages (30d/90d/180d)")
        avgs = fetch_sofr_averages()
        if not avgs.empty:
            for rt in avgs['rate_type'].unique():
                subset = avgs[avgs['rate_type'] == rt].copy()
                last = connection.get_last_by(
                    table_name=TABLE,
                    column_name='fecha',
                    filter_by=('rate_type', rt)
                )
                last_date = last[0]['fecha'] if len(last) > 0 else None
                if last_date:
                    subset = subset[subset['fecha'] > last_date]
                if not subset.empty:
                    subset = subset.where(subset.notna(), None)
                    connection.insert_dataframe(frame=subset, table_name=TABLE)
                    print(f"  {rt}: inserted {len(subset)} rows")
                else:
                    print(f"  {rt}: up to date")
        else:
            print(f"  No SOFR averages data")
    finally:
        connection.close()

    print(f"\nDone!")


if __name__ == "__main__":
    main()
