"""
Runner: Collect SOFR OIS par swap curve from Eris Futures.
Stores in xerenity.sofr_swap_curve table.
Incremental load — only inserts dates after the last stored date.
First load fetches ~3 months of history.

Schedule: Daily at 21:00 UTC (Eris publishes ~15:40 ET)
"""

from datetime import date, timedelta
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.eris_sofr.ErisSofrCollector import fetch_sofr_curve_range

TABLE = 'sofr_swap_curve'


def main():
    print(f"SOFR Swap Curve Collector - {date.today()}")

    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    try:
        last = connection.get_last_by(
            table_name=TABLE,
            column_name='fecha',
        )

        last_date = last[0]['fecha'] if len(last) > 0 else None
        print(f"  Last stored date: {last_date or 'none (first load)'}")

        if last_date:
            start = date.fromisoformat(last_date) + timedelta(days=1)
        else:
            start = date.today() - timedelta(days=90)

        df = fetch_sofr_curve_range(start, date.today())

        if df.empty:
            print("  Already up to date (or no new data)")
            return

        print(f"  Fetched {len(df)} data points")
        print(f"  Dates: {df['fecha'].min()} to {df['fecha'].max()}")

        try:
            connection.insert_data_frame_one_shot(frame=df, table_name=TABLE)
            print(f"  Inserted {len(df)} rows")
        except Exception as e:
            print(f"  One-shot failed ({e}), inserting row by row...")
            connection.insert_dataframe(frame=df, table_name=TABLE)
            print(f"  Inserted rows (with duplicate handling)")

    finally:
        connection.close()

    print(f"\nDone!")


if __name__ == "__main__":
    main()
