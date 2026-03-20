import requests
import pandas as pd
import io
from datetime import datetime, timedelta
from data_collectors.DataCollector import DataCollector

class UsuryRateCollector(DataCollector):

    def __init__(self):
        super().__init__(name='tasa_usura')

        self.session = requests.session()

        self.base_url = 'https://www.superfinanciera.gov.co/loader.php?lServicio=Tools2&lTipo=descargas&lFuncion=descargar&idFile=1069287'

        self.params = {
            "Format": "xls",
            "Extension": ".xls",
            "BypassCache": True,
            "lang": "es",
            "SyncOperation": "1"
            }


    def get_stock_price(self, columns = None, from_date=datetime.today(),
                        to_date=datetime.today().strftime('%Y-%m-%d')):

        header_dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0"
        }

        response = self.session.get(url=self.base_url, params=self.params, stream=True, headers=header_dict)

        print(response.status_code)

        if response.status_code in range(200, 210):
            response_bytes = io.BytesIO(response.content)
            df = pd.read_excel(response_bytes)
            df = df.iloc[291:,[0,3]]
            df.rename(columns = {'Unnamed: 0' : 'fecha', 'Unnamed: 3' : 'tasa_usura'}, inplace= True)
            df = df.loc[pd.to_numeric(df['fecha'].astype(str).str.slice(0,4), errors='coerce') > 0,:]
            df = df.loc[df['tasa_usura'].notnull(),:]
            df['fecha'] = pd.to_datetime(df['fecha'], format="%Y-%m-%d %H:%M:%S'")
            df['fecha'] = df['fecha'].dt.strftime("%Y-%m-%d")
            return df
        else:
            print(response.status_code)



#historic from manually generated xlsx file

# df_historic = pd.read_excel("historic_usury.xlsx", sheet_name= "usura_histórico")

# df_historic['series_id'] = 'Ordinario'

# df_historic['key_id'] = df_historic['fecha'].astype(str) + '_' +df_historic['series_id']

# df_historic['fecha'] = df_historic['fecha'].dt.strftime("%Y-%m-%d")

# df_historic.head()

# df_historic.to_clipboard()

# from db_connection.supabase.Client import SupabaseConnection
# connection = SupabaseConnection()
# connection.sign_in_as_collector()

# connection.insert_dataframe(frame=df_historic, table_name='tasa_usura')

