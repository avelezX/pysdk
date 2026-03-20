import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector

class BankForInternationalSettlements(DataCollector):
    def __init__(self, name):
        super().__init__(name)
        self.session = requests.session()
        self.base_url = "https://data.bis.org/topics/CBPOL/BIS%2CWS_CBPOL%2C1.0/M.{}?view=observations&file_format=csv&format=long&include=code%2Clabel"

    def get_price(self, country_code: str, days_back=7):
        url = f"{self.base_url.format(country_code)}&lastNObservations={days_back}"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"Error descargando {country_code}: {response.status_code}")
            return None

        try:
            df = pd.read_csv(StringIO(response.text), skiprows=6)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

            print(f"\n🔍 Columnas recibidas para {country_code}:")
            print(df.columns.tolist())
            print(df.head(5))

            if df.shape[1] != 10:
                raise ValueError("Formato de columnas inesperado")

            df.columns = [
                "dataset", "serie", "frecuencia", "pais", "unidad", "unidad2",
                "fecha", "licencia", "atributo", "dato"
            ]

            print(f"\n🔎 Explorando posibles columnas con país:")
            ejemplo_pais = df['pais'].iloc[0] if not df.empty else None
            if ejemplo_pais and ":" in ejemplo_pais:
                print(f"✅ Posible columna país: 'pais' - Ejemplo: {ejemplo_pais}")
            else:
                print(f"❌ No se detectó formato esperado en columna país")

            df["fecha"] = pd.to_datetime(df["fecha"])

            # Hacemos split para código y nombre
            df[["codigo", "nombre"]] = df["pais"].str.split(":", expand=True)

            print(f"\n🔎 Primeros códigos y nombres extraídos:")
            print(df[["codigo", "nombre"]].head())

            df["valor"] = df["dato"]
            df["key_id"] = df["codigo"] + "_" + df["fecha"].dt.strftime("%Y-%m-%d")

            return df[["fecha", "codigo", "nombre", "valor", "key_id"]].reset_index(drop=True)

        except Exception as e:
            print(f"❌ Error procesando {country_code}: {e}")
            return None


        