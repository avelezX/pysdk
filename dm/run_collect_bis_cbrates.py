from data_collectors.bis.bis_collector import BankForInternationalSettlements
from db_connection.supabase.Client import SupabaseConnection
import pandas as pd

connection = SupabaseConnection()
connection.sign_in_as_collector()

bis = BankForInternationalSettlements(name="InterestRateCollector")

paises = [
    "AR", "AU", "AT", "BE", "BR", "CA", "CL", "CN", "CO", "HR", "CZ", "DK", "XM", "FR", "DE", "GR",
    "HK", "HU", "IS", "IN", "ID", "IL", "IT", "JP", "KR", "KW", "MY", "MX", "MA", "NL", "NZ", "MK",
    "NO", "PE", "PH", "PL", "PT", "RO", "RU", "SA", "RS", "ZA", "ES", "SE", "CH", "TH", "TR", "GB", "US"
]

for pais in paises:
    try:
        print(f"\n🌎 Procesando país: {pais}")
        df = bis.get_price(country_code=pais, days_back=7)

        if df is not None and len(df) > 0:
            last = connection.get_last_by(
                table_name='cb_rates',
                column_name='fecha',
                filter_by=('codigo', pais)
            )

            if len(last) > 0:
                filter_date = pd.to_datetime(last[0]['fecha'])
                df = df[df['fecha'] > filter_date].copy(deep=True)

            if len(df) > 0:
                df['fecha'] = df['fecha'].astype(str)
                connection.insert_dataframe(frame=df, table_name='cb_rates')
                print(f"✅ Insertados {len(df)} registros para {pais}")
            else:
                print("ℹ️ No hay datos nuevos para insertar.")

        else:
            print("ℹ️ Sin datos descargados.")

    except Exception as e:
        print(f"❌ Error guardando {pais}: {e}")



