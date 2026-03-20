##%
import sys
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.forward_rates.fwd_rates_collector import ForwardRateCollector
import datetime
from datetime import timedelta

collector = ForwardRateCollector('fwd_collector')
connection = SupabaseConnection()

connection.sign_in_as_collector()

update_insert: bool = True

interval_tenors = [1, 3, 6, 12]

quotes = connection.read_table_limit(table_name='ibr_quotes_curve', limit=1)

for x in interval_tenors:
    fwd_curve = collector.get_ibr_quotes(ibr_quotes=quotes, interval_tenor=x, )

    table_name = 'ibr_implicita_{}m'.format(x)

    connection.delete_where_colum_is_not_null(table_name=table_name, column_name='fecha')

    connection.insert_dataframe(frame=fwd_curve, table_name=table_name)
