import sys
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.uvr_prints.uvr_prints_collector import IbrPrintsCollector
import datetime
from datetime import timedelta
import pandas as pd

collector = IbrPrintsCollector('ivr_collector')
connection = SupabaseConnection()

connection.sign_in_as_collector()

update_insert: bool = True

dic_series = {
    "Tasa de Politica Monetaria": 8,
    "Unidad de Valor Real (UVR)": 19
}

uvr_data = connection.read_table_limit(
    table_name='banrep_series_value_v2',
    limit=365 * 2,
    filter_by=('id_serie', dic_series['Unidad de Valor Real (UVR)']),
    order_by='fecha',
    order_desc=True
)

cbr_data = connection.read_table_limit(
    table_name='banrep_series_value_v2',
    limit=1,
    filter_by=('id_serie', dic_series['Tasa de Politica Monetaria'])
)[0]['valor']

tes_data = connection.read_table(table_name='tes')

index_change = {
    'lag_value': 12,
    'id_canasta_search': 1
}

last_cpi_data = connection.rpc('cpi_index_change', index_change)

df = pd.DataFrame(last_cpi_data)
df.rename(columns={'value': 'percentage_change'}, inplace=True)
df = df.sort_index()
last_cpi = df['percentage_change'].iloc[-1]

col_tes = connection.rpc('get_tes_grid_raw', {'money': 'COLTES-COP'})
col_tes_uvr = connection.rpc('get_tes_grid_raw', {'money': 'COLTES-UVR'})
col_tes.extend(col_tes_uvr)

# Last CPI lag
index_change = {
    'id_canasta_search': 1
}

last_cpi_lag_data = connection.rpc('cpi_index_nochange', index_change)

last_cpi_lag_df = pd.DataFrame(last_cpi_lag_data)
last_cpi_lag_df.rename(columns={'value': 'cpi_index'}, inplace=True)
last_cpi_lag_df.rename(columns={'time': 'fecha'}, inplace=True)
last_cpi_lag_0 = last_cpi_lag_df.to_dict(orient="records")

uvr_prints_data = collector.get_ibr_quotes(
    uvr=uvr_data,
    cbr=cbr_data,
    tes_table=tes_data,
    last_cpi=last_cpi,
    last_cpi_lag_0=last_cpi_lag_0,
    col_tes=col_tes
)

deletion = connection.delete_where_colum_is_not_null(table_name='uvr_projection', column_name='fecha')

connection.insert_dataframe(frame=uvr_prints_data, table_name='uvr_projection')

cpi_implicit = collector.get_cpi_implicit(
    uvr=uvr_data,
    cbr=cbr_data,
    tes_table=tes_data,
    last_cpi=last_cpi,
    last_cpi_lag_0=last_cpi_lag_0,
    col_tes=col_tes
)


connection.delete_where_colum_is_not_null(table_name='inflacion_implicita', column_name='fecha')

connection.insert_dataframe(frame=cpi_implicit, table_name='inflacion_implicita')
