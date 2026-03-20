"""
Camacol Construction Series Collector
Reads data/series_camacol_completo.xlsx and loads 29 normalized time series
into xerenity.camacol_series_value.
Incremental: only inserts rows newer than the last stored date per series.
"""
import os
from data_collectors.camacol.CamacolCollector import CamacolCollector
from db_connection.supabase.Client import SupabaseConnection

EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'series_camacol_completo.xlsx')

# Connect to Supabase as collector
connection = SupabaseConnection()
connection.sign_in_as_collector()

# Extract all series
collector = CamacolCollector(excel_path=EXCEL_PATH)
frames = collector.extract_all()

# Insert incrementally
success = 0
failures = 0

for df in frames:
    serie_id = int(df['id_serie'].iloc[0])
    try:
        last = connection.get_last_by(
            table_name='camacol_series_value',
            column_name='fecha',
            filter_by=('id_serie', serie_id)
        )

        if len(last) > 0:
            filter_date = last[0]['fecha']
            new_rows = df[df['fecha'] > filter_date].copy(deep=True)
        else:
            new_rows = df.copy(deep=True)

        if len(new_rows) > 0:
            connection.insert_dataframe(frame=new_rows, table_name='camacol_series_value')
            print(f'Serie {serie_id}: {len(new_rows)} new rows inserted')
            success += 1
        else:
            print(f'Serie {serie_id}: up to date')
            success += 1
    except Exception as e:
        failures += 1
        print(f'Failed serie {serie_id}: {e}')

print(f'\nCollection complete: {success} successful, {failures} failures, {len(frames)} total series')
