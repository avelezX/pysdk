from db_connection.supabase.Client import SupabaseConnection
from data_collectors.dtcc.IBR_swap import IBRSwapCollector
import datetime
from datetime import timedelta

col = IBRSwapCollector()

# Si se quiere hacer un llamado de un dia puntual usar el formato date_call = datetime.datetime(2024,1,29,23,0,0)

date_call = datetime.datetime.now()
# yesterday = date_call - timedelta(days=168)

connection = SupabaseConnection()

connection.sign_in_as_collector()

update_insert: bool = True
days = 1
for x in range(0, days):

    yesterday = date_call - timedelta(days=x)

    print('--------IBR FOR--------')
    print(yesterday)
    print('-----------------------')

    dataframe = col.get_raw_data(yesterday)

    if len(dataframe) > 0:
        cleaned_data = col.clean_raw_data_1(dataframe=dataframe, columns=col.columns, eq_operator=True)

        mods = col.clean_raw_data_1(dataframe=dataframe, columns=col.columns, eq_operator=False)

        if update_insert:
            connection.insert_dataframe(frame=cleaned_data, table_name='ibr_swaps')

            mods = mods.rename(columns={'dissemination_identifier': 'update_identifier'})

            mods.drop('action_type', inplace=True, axis=1)

            connection.update_given_dataframe(
                frame=mods,
                table_name='ibr_swaps',
                eq_column='dissemination_identifier',
                eq_row_name='original_dissemination_identifier'
            )
