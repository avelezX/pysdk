from datetime import datetime
import pandas as pd
import traceback
from data_collectors.alphacast.alphacast_collector import AlphacastEMBICollector
from db_connection.supabase.Client import SupabaseConnection


DAYS_BACK = 7
API_KEY = "ak_omAffDqHgquwbsqWtVu7"
DATASET_ID = 5293

LATAM_COUNTRIES = [
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Costa Rica", "Cuba", "Ecuador",
    "El Salvador", "Guatemala", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay",
    "Peru", "Dominican Republic", "Uruguay", "Venezuela", "Puerto Rico"
]

connection = SupabaseConnection()
connection.sign_in_as_collector()


embi_collector = AlphacastEMBICollector(api_key=API_KEY, dataset_id=DATASET_ID)

try:
    print(f"\n🔄 Descargando datos de los últimos {DAYS_BACK} días desde Alphacast...")
    data_frame = embi_collector.get_price(days_back=DAYS_BACK)

    if len(data_frame) == 0:
        print("⚠️ No se encontraron datos en el período indicado.")
    else:
        print(f"✅ Datos descargados: {len(data_frame)} registros totales.")
        print(f"📅 Fechas disponibles: {data_frame['time'].min()} a {data_frame['time'].max()}")

    for country in LATAM_COUNTRIES:
        df_country = data_frame[data_frame['country'].str.lower() == country.lower()]
        print(f"\n🌎 Procesando país: {country} ({len(df_country)} registros)")

        if df_country.empty:
            print("ℹ️ No se encontraron datos para este país.")
            continue

        last = connection.get_last_by(
            table_name='embi',
            column_name='time',
            filter_by=('country', country)
        )

        if len(last) > 0:
            last_time = last[0]['time']
            print(f"🕒 Último dato en base de datos para {country}: {last_time}")
            filtering = df_country[df_country['time'] > last_time].copy(deep=True)
        else:
            print(f"🆕 No hay datos previos para {country}, insertando todo.")
            filtering = df_country.copy(deep=True)

        if filtering.empty:
            print(f"ℹ️ No hay datos nuevos para insertar para {country}.")
            continue

        filtering['time'] = filtering['time'].astype(str)

        # ✅ Reemplaza NaNs por None para compatibilidad con JSON
        filtering = filtering.where(pd.notnull(filtering), None)

        print(f"⬆️ Insertando {len(filtering)} nuevos registros en Supabase para {country}...")
        connection.insert_dataframe(frame=filtering, table_name='embi')

except Exception as e:
    print('❌ Error al guardar datos EMBI:')
    traceback.print_exc()

print("\n✅ Proceso completo.")
