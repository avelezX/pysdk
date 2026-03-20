# import sys
# sys.path.append('/Users/avelezxerenity/Documents/GitHub/xerenity-dm')
from db_connection.supabase.Client import SupabaseConnection
from datetime import datetime, timedelta
from data_collectors.fic_govt.interes_creditos import Int_CredCollector

int_cred = Int_CredCollector()
connection = SupabaseConnection()
connection.sign_in_as_collector()

raw_data = int_cred.get_raw_data()

clean_data = int_cred.clean_raw_data(raw_data)

if clean_data is not None and len(clean_data) > 0:
    last = connection.get_last_by(
        table_name='interes_creditos',
        column_name='fecha_corte'
    )
    if len(last) > 0:
        filter_date = last[0]['fecha_corte']
        filtering = clean_data[clean_data['fecha_corte'] > filter_date].copy(deep=True)
    else:
        filtering = clean_data.copy(deep=True)

    if len(filtering) > 0:
        connection.insert_dataframe(frame=filtering, table_name='interes_creditos')

clean_data_aggregated = int_cred.clean_raw_data_aggregate(raw_data)

if clean_data_aggregated is not None and len(clean_data_aggregated) > 0:
    last_agg = connection.get_last_by(
        table_name='interes_creditos_modalidad',
        column_name='fecha_corte'
    )
    if len(last_agg) > 0:
        filter_date_agg = last_agg[0]['fecha_corte']
        filtering_agg = clean_data_aggregated[clean_data_aggregated['fecha_corte'] > filter_date_agg].copy(deep=True)
    else:
        filtering_agg = clean_data_aggregated.copy(deep=True)

    if len(filtering_agg) > 0:
        connection.insert_dataframe(frame=filtering_agg, table_name='interes_creditos_modalidad')
