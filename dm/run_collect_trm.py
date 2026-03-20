from db_connection.supabase.Client import SupabaseConnection
from data_collectors.fic_govt.trm import trmCollector

trm = trmCollector()

connection = SupabaseConnection()

connection.sign_in_as_collector()

raw_data = trm.get_raw_data(days=100)

clean_data = trm.clean_raw_data_1(raw_data)

if len(clean_data) > 0:

    last = connection.get_last_by(table_name='currency', column_name='time',
                                  filter_by=('currency', 'USD:COP'))

    if len(last) > 0:
        filter_date = last[0]['time']
        filtering = clean_data[clean_data['time'] > filter_date].copy(deep=True)
    else:
        filtering = clean_data.copy(deep=True)

    filtering['time'] = filtering['time'].astype(str)

    connection.insert_dataframe(frame=filtering, table_name='currency')
