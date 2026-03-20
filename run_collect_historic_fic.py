import sys
sys.path.append('C:/GitHub/xerenity-dm')

from data_collectors.dane.dane_data_collector import DaneCollector
from datetime import datetime
from db_connection.supabase.Client import SupabaseConnection

from data_collectors.fic_govt.fic_historic_recolector import fic_historical_colector

connection = SupabaseConnection()
connection.sign_in_as_collector()


for full_dataframe in fic_historical_colector():
    if full_dataframe is not None and not full_dataframe.empty:
        connection.insert_dataframe(frame=full_dataframe, table_name='fic_v3')
