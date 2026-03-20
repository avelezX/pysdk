from data_collectors.suameca.SuamecaCollector import SuamecaCollector
from db_connection.supabase.Client import SupabaseConnection

# IBR series mapping: suameca_id -> internal id_serie in banrep_series_value_v2
IBR_SERIES = [
    {"suameca_id": 241,   "internal_id": 9,  "name": "IBR-ON"},
    {"suameca_id": 242,   "internal_id": 11, "name": "IBR-1N"},
    {"suameca_id": 243,   "internal_id": 13, "name": "IBR-3N"},
    {"suameca_id": 16560, "internal_id": 15, "name": "IBR-6N"},
    {"suameca_id": 16562, "internal_id": 17, "name": "IBR-12N"},
]

TABLE_NAME = "banrep_series_value_v2"


def get_existing_dates(connection, internal_id):
    """
    Fetch all existing fechas for a given id_serie from banrep_series_value_v2.
    Returns a set of date strings (YYYY-MM-DD).
    Uses pagination to handle series with more than 1000 rows.
    """
    existing = set()
    page_size = 1000
    offset = 0

    while True:
        rows = (
            connection.supabase
            .table(TABLE_NAME)
            .select("fecha")
            .eq("id_serie", internal_id)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break
        for row in rows:
            existing.add(row["fecha"])
        if len(rows) < page_size:
            break
        offset += page_size

    return existing


def refresh_ibr_loan_curves(connection):
    """
    Call xerenity.update_ibr_loan_curves() via Supabase RPC
    to refresh the ibr_quotes_curve materialized view.
    """
    print("\nRefreshing ibr_quotes_curve materialized view...")
    try:
        connection.rpc("update_ibr_loan_curves", {})
        print("ibr_quotes_curve refreshed successfully.")
    except Exception as e:
        print(f"Warning: RPC update_ibr_loan_curves failed: {e}")


def main():
    print("=== IBR SUAMECA Backfill ===")
    print(f"Processing {len(IBR_SERIES)} IBR series: " +
          ", ".join(
              f"{s['name']} (suameca_id={s['suameca_id']}, id_serie={s['internal_id']})"
              for s in IBR_SERIES
          ))

    collector = SuamecaCollector()
    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    # Fetch ALL historical data for all 5 IBR series in one batch API call
    print("\nFetching ALL available data from SUAMECA for IBR series...")
    frames = collector.get_batch_series_data(IBR_SERIES)

    if not frames:
        print("ERROR: No data returned from SUAMECA. Aborting.")
        return

    total_inserted = 0
    total_skipped = 0
    failures = 0

    for serie in IBR_SERIES:
        internal_id = serie["internal_id"]
        name = serie["name"]
        suameca_id = serie["suameca_id"]

        df = frames.get(internal_id)

        if df is None or len(df) == 0:
            print(f"\n[{name}] No data returned from SUAMECA (suameca_id={suameca_id}), skipping.")
            continue

        print(f"\n[{name}] Fetched {len(df)} rows from SUAMECA.")

        # Fetch all existing dates for this series from the DB to deduplicate
        print(f"[{name}] Fetching existing dates from DB...")
        try:
            existing_dates = get_existing_dates(connection, internal_id)
            print(f"[{name}] Found {len(existing_dates)} existing rows in DB.")
        except Exception as e:
            print(f"[{name}] ERROR fetching existing dates: {e}. Skipping series.")
            failures += 1
            continue

        # Filter to only new rows not yet in the DB
        new_rows = df[~df["fecha"].isin(existing_dates)].copy(deep=True)

        if len(new_rows) == 0:
            print(f"[{name}] No new rows to insert (all {len(df)} rows already in DB).")
            total_skipped += len(df)
            continue

        skipped = len(df) - len(new_rows)
        print(f"[{name}] Inserting {len(new_rows)} new rows ({skipped} already existed in DB)...")

        try:
            connection.insert_dataframe(frame=new_rows, table_name=TABLE_NAME)
            total_inserted += len(new_rows)
            total_skipped += skipped
            print(f"[{name}] Done.")
        except Exception as e:
            print(f"[{name}] ERROR during insert: {e}")
            failures += 1

    print(f"\n=== Backfill Summary ===")
    print(f"  Inserted : {total_inserted} rows")
    print(f"  Skipped  : {total_skipped} rows (already existed)")
    print(f"  Failures : {failures} series")

    # Refresh the ibr_quotes_curve materialized view after writing
    refresh_ibr_loan_curves(connection)

    print("\nBackfill complete.")


if __name__ == "__main__":
    main()