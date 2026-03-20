import sys
sys.path.append('C:/GitHub/xerenity-dm')
import requests
import pandas as pd

from data_collectors.dtcc.dtcc_collector import DttcColelctor


class Int_CredCollector(DttcColelctor):
    def __init__(self):

        super().__init__(name = 'int_cred')
      
        self.last_date = requests.get('https://www.datos.gov.co/resource/w9zh-vetq.json?$select=max(fecha_corte)')

        self.url = 'https://www.datos.gov.co/resource/w9zh-vetq.json?$limit=10000000&fecha_corte='+ self.last_date.json()[0]['max_fecha_corte']
        
    def get_raw_data(self):

        print(self.url)
        return requests.get(self.url)
    
    def clean_raw_data(self, row_data_json):

        if row_data_json.status_code == 200:
            # Append the dataframe
            df = pd.DataFrame(row_data_json.json())

            # Convert series to numeric for aggregation
            df['tasa_efectiva_promedio'] = pd.to_numeric(df['tasa_efectiva_promedio'])
            df['montos_desembolsados'] = pd.to_numeric(df['montos_desembolsados'])
            
            # Aggregate by the breakdowns of interest and obtain weighted average of the variable of interes, the interest rate  
            df['tasa_times_monto'] = df.tasa_efectiva_promedio*df.montos_desembolsados
            breakdowns = ['fecha_corte','codigo_entidad', 'nombre_tipo_entidad', 'nombre_entidad', 'tipo_de_cr_dito', 'plazo_de_cr_dito']
            df_agg = df.groupby(breakdowns).agg(Numerator =('tasa_times_monto', 'sum'), monto_desembolsado = ('montos_desembolsados', 'sum')).reset_index()
            df_agg['tasa_efectiva_promedio'] = df_agg['Numerator']/df_agg['monto_desembolsado']
            df_agg.drop(columns = ['Numerator'], inplace=True)
            df_agg.rename(columns = {"fecha_corte" : "fecha_corte",
                                    "nombre_tipo_entidad" : "tipo_entidad",
                                    "nombre_entidad" : "nombre_entidad",
                                    "tipo_de_cr_dito" : "tipo_de_credito",
                                    "plazo_de_cr_dito" : "plazo_de_credito",
                                    "monto_desembolsado" : "monto_desembolsado"}, inplace= True)

            # Create key id to ensure row uniquenes
            df_agg['key_id'] = df_agg['fecha_corte'].astype(str).str[:10] + '_' + df_agg['nombre_entidad'].astype(str) + '_' + df_agg['tipo_de_credito'].astype(str) + '_' + df_agg['plazo_de_credito'].astype(str)

            # Remove accents, tildes, capital letters from the key to ensure unified keys
            df_agg['key_id'] = df_agg['key_id'].str.lower()

            # Clean wrong special characters in: nombre_patrimonio
            patt = ['ñ', 'á', 'é', 'í','ó', 'u', ' ', '.']

            repl = ['n', 'a', 'e', 'i', 'o', 'u', '', '.']

            for i, j in zip(patt, repl):
                df_agg['key_id'] = df_agg['key_id'].str.replace(i, j)

            # create series id
            df_agg['series_id'] = df_agg['key_id'].str[11:]

            # Hash both key id and series id
            df_agg['key_id'] = pd.util.hash_pandas_object(df_agg['key_id'],
                                        index = False, 
                                        hash_key='0123456789123456')

            df_agg['series_id'] = pd.util.hash_pandas_object(df_agg['series_id'],
                                        index = False, 
                                        hash_key='0123456789123456') 
    
            return df_agg
        else:
            print(row_data_json.status_code)

    def clean_raw_data_aggregate(self, row_data_json):

        if row_data_json.status_code == 200:
            # Append the dataframe
            df = pd.DataFrame(row_data_json.json())

            # Convert series to numeric for aggregation
            df['tasa_efectiva_promedio'] = pd.to_numeric(df['tasa_efectiva_promedio'])
            df['montos_desembolsados'] = pd.to_numeric(df['montos_desembolsados'])
            
            # Aggregate by the breakdowns of interest and obtain weighted average of the variable of interes, the interest rate  
            df['tasa_times_monto'] = df.tasa_efectiva_promedio*df.montos_desembolsados
            breakdowns = ['fecha_corte', 'tipo_de_cr_dito']
            df_agg = df.groupby(breakdowns).agg(Numerator =('tasa_times_monto', 'sum'), monto_desembolsado = ('montos_desembolsados', 'sum')).reset_index()
            df_agg['tasa_efectiva_promedio'] = df_agg['Numerator']/df_agg['monto_desembolsado']
            df_agg.drop(columns = ['Numerator'], inplace=True)
            df_agg.rename(columns = {"fecha_corte" : "fecha_corte",
                                    "tipo_de_cr_dito" : "tipo_de_credito",
                                    "monto_desembolsado" : "monto_desembolsado"}, inplace= True)

            # Create key id to ensure row uniquenes
            df_agg['key_id'] = df_agg['fecha_corte'].astype(str).str[:10] + '_' + df_agg['tipo_de_credito'].astype(str)

            # Remove accents, tildes, capital letters from the key to ensure unified keys
            df_agg['key_id'] = df_agg['key_id'].str.lower()

            # Clean wrong special characters in: nombre_patrimonio
            patt = ['ñ', 'á', 'é', 'í','ó', 'u', ' ', '.']

            repl = ['n', 'a', 'e', 'i', 'o', 'u', '', '.']

            for i, j in zip(patt, repl):
                df_agg['key_id'] = df_agg['key_id'].str.replace(i, j)

            # create series id
            df_agg['series_id'] = df_agg['key_id'].str[11:]

            # Hash both key id and series id
            df_agg['key_id'] = pd.util.hash_pandas_object(df_agg['key_id'],
                                        index = False, 
                                        hash_key='0123456789123456')

            df_agg['series_id'] = pd.util.hash_pandas_object(df_agg['series_id'],
                                        index = False, 
                                        hash_key='0123456789123456') 
    
            return df_agg
        else:
            print(row_data_json.status_code)        
    
    