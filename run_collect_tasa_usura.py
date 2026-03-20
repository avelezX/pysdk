import datetime as dt
from data_collectors.banrep_stats.banrep_data_file_collector import BanrepDataCollector
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.fic_govt.tasa_usura import UsuryRateCollector

connection = SupabaseConnection()
connection.sign_in_as_collector()
usura = UsuryRateCollector()


try:
    df = usura.get_stock_price()
    df['series_id'] = 'Ordinario'
 
    last = connection.get_last_by(
        table_name='tasa_usura',
        column_name='fecha',
        filter_by=('series_id', 'Ordinario')
    )

    if len(last) > 0:
        filter_date = last[0]['fecha']
        filtering = df[df['fecha'] > filter_date].copy(deep=True)
    else:
        filtering = df.copy(deep=True)

    connection.insert_dataframe(frame=filtering, table_name='tasa_usura')

except Exception as e:
    print("Failed to retrieve last usury data: {}".format(str(e)))