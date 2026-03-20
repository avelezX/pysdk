import sys
sys.path.append('C:/GitHub/xerenity-dm')

import requests
import pandas as pd
from db_connection.supabase.Client import SupabaseConnection
from datetime import datetime, timedelta

# Sandbox

distinct_date = requests.get('https://www.datos.gov.co/resource/w9zh-vetq.json?$select=distinct fecha_corte')

distinct_date_df = pd.DataFrame(distinct_date.json())

for i in distinct_date_df['fecha_corte']:

    url = 'https://www.datos.gov.co/resource/w9zh-vetq.json?$limit=20000000&fecha_corte=' + i

    raw = requests.get(url)

    if raw.status_code == 200:
            # Append the dataframe
            df = pd.DataFrame(raw.json())

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
    

    connection = SupabaseConnection()
    connection.sign_in_as_collector()
    connection.insert_dataframe(frame=df_agg, table_name='interes_creditos_modalidad')

else:
    print(raw.status_code)
