from datetime import datetime, timedelta
import pandas as pd
from alphacast import Alphacast

class AlphacastEMBICollector:
    def __init__(self, api_key, dataset_id):
        self.api_key = api_key
        self.dataset_id = dataset_id
        self.client = Alphacast(api_key=self.api_key)

    def get_price(self, days_back=4):
        df = self.client.datasets.dataset(self.dataset_id).download_data(format="pandas")

        if df.empty:
            print("⚠️ No se encontraron datos en el dataset.")
            return pd.DataFrame()

        country_col = next((col for col in df.columns if col.lower() in ['country', 'pais', 'país']), None)
        date_col = next((col for col in df.columns if col.lower() == 'date'), None)
        embi_col = "EMBI Global Diversified Subindices"

        if not (country_col and date_col and embi_col in df.columns):
            raise Exception("❌ No se encontraron las columnas necesarias en el dataset.")

        df[date_col] = pd.to_datetime(df[date_col])
        from_date = datetime.utcnow() - timedelta(days=days_back)
        df_filtered = df[df[date_col] >= from_date]

        df_filtered = df_filtered[[country_col, date_col, embi_col]].rename(columns={
            country_col: "country",
            date_col: "time",
            embi_col: "value"
        })

        return df_filtered