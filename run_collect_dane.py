from data_collectors.dane.dane_data_collector import DaneCollector
from datetime import datetime

from db_connection.supabase.Client import SupabaseConnection

connection = SupabaseConnection()

connection.sign_in_as_collector()

dane = DaneCollector()

current_date = datetime.now()

current_month = current_date.month
current_year = current_date.year

if current_month == 1:
    current_month = 12
    current_year -= 1
else:
    current_month -= 1

print('Collecting values for  {} {}'.format(current_month, current_year))
values = dane.get_cleaned_raw_data(month=current_month, year=current_year)
connection.insert_json_array(json_objs=values, table_name='canasta_values')
