"""
BCRP (Banco Central de Reserva del Peru) Series Collector
Fetches economic series from BCRP public API and inserts into xerenity.bcrp_series_value.
Designed to run daily via cron/scheduler.

API docs: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api
No API key required.
"""

from datetime import datetime
from data_collectors.bcrp.BcrpCollector import BcrpCollector
from db_connection.supabase.Client import SupabaseConnection

TABLE_NAME = 'bcrp_series_value'

# Series to collect from BCRP
# Each entry: (id, bcrp_code, series_name, frequency)
# frequency: 'D' = daily, 'M' = monthly
SERIES = [
    # --- Tipo de Cambio (Daily) ---
    {
        'id': 101,
        'code': 'PD04637PD',
        'name': 'TC Interbancario Compra',
        'frequency': 'D',
    },
    {
        'id': 102,
        'code': 'PD04638PD',
        'name': 'TC Interbancario Venta',
        'frequency': 'D',
    },
    {
        'id': 103,
        'code': 'PD04639PD',
        'name': 'TC SBS Compra',
        'frequency': 'D',
    },
    {
        'id': 104,
        'code': 'PD04640PD',
        'name': 'TC SBS Venta',
        'frequency': 'D',
    },

    # --- Tasas de Interes (Daily) ---
    {
        'id': 105,
        'code': 'PD04692MD',
        'name': 'Tasa Interbancaria PEN',
        'frequency': 'D',
    },
    {
        'id': 106,
        'code': 'PD04693MD',
        'name': 'Tasa Interbancaria USD',
        'frequency': 'D',
    },
    {
        'id': 107,
        'code': 'PD12301MD',
        'name': 'Tasa de Referencia Politica Monetaria',
        'frequency': 'D',
    },

    # --- Tasa Maxima Compensatoria (Daily) ---
    {
        'id': 108,
        'code': 'PD38590DD',
        'name': 'Tasa Maxima Compensatoria MN',
        'frequency': 'D',
    },
    {
        'id': 109,
        'code': 'PD38591DD',
        'name': 'Tasa Maxima Compensatoria ME',
        'frequency': 'D',
    },

    # --- Bonos Gobierno (Daily) ---
    {
        'id': 110,
        'code': 'PD31893DD',
        'name': 'Bono Gobierno PEN 10Y',
        'frequency': 'D',
    },
    {
        'id': 111,
        'code': 'PD31894DD',
        'name': 'Bono Gobierno USD 10Y',
        'frequency': 'D',
    },

    # --- Tasas Promedio (Monthly) ---
    {
        'id': 120,
        'code': 'PN07807NM',
        'name': 'TAMN (Tasa Activa MN)',
        'frequency': 'M',
    },
    {
        'id': 121,
        'code': 'PN07827NM',
        'name': 'TAMEX (Tasa Activa ME)',
        'frequency': 'M',
    },
    {
        'id': 122,
        'code': 'PN07816NM',
        'name': 'TIPMN (Tasa Pasiva MN)',
        'frequency': 'M',
    },
    {
        'id': 123,
        'code': 'PN07836NM',
        'name': 'TIPMEX (Tasa Pasiva ME)',
        'frequency': 'M',
    },

    # --- Inflacion (Monthly) ---
    {
        'id': 130,
        'code': 'PN38705PM',
        'name': 'IPC Lima Metropolitana',
        'frequency': 'M',
    },
    {
        'id': 131,
        'code': 'PN01273PM',
        'name': 'IPC Variacion 12 meses',
        'frequency': 'M',
    },
]


def main():
    collector = BcrpCollector()
    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    for serie in SERIES:
        serie_id = serie['id']
        code = serie['code']
        name = serie['name']
        freq = serie['frequency']

        print(f'\n--- Collecting: {name} ({code}) ---')

        try:
            # Fetch from BCRP API
            # BCRP API rejects future end dates, so use current date
            now = datetime.today()
            if freq == 'D':
                from_date = '2015-1-1'
                to_date = f'{now.year}-{now.month}-{now.day}'
            else:
                from_date = '2015-1'
                to_date = f'{now.year}-{now.month}'

            results = collector.get_series([code], from_date, to_date)
            df = results.get(code)

            if df is None or df.empty:
                print(f'  No data returned for {name}')
                continue

            # Add id_serie column
            df['id_serie'] = serie_id

            print(f'  Downloaded {len(df)} records')

            # Check for existing data to avoid duplicates
            last = connection.get_last_by(
                table_name=TABLE_NAME,
                column_name='fecha',
                filter_by=('id_serie', serie_id)
            )

            if len(last) > 0:
                filter_date = last[0]['fecha']
                print(f'  Last record in DB: {filter_date}')
                filtering = df[df['fecha'] > filter_date].copy(deep=True)
            else:
                print(f'  No existing data, inserting all records.')
                filtering = df.copy(deep=True)

            if filtering.empty:
                print(f'  No new data to insert for {name}')
                continue

            print(f'  Inserting {len(filtering)} new records...')
            connection.insert_dataframe(frame=filtering, table_name=TABLE_NAME)
            print(f'  Done: {name}')

        except Exception as e:
            print(f'  Error collecting {name}: {e}')
            continue

    print('\n--- BCRP collection complete ---')


if __name__ == '__main__':
    main()
