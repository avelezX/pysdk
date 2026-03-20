
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.fic_govt.fic import ficCollector
from datetime import datetime, timedelta

col = ficCollector()
connection = SupabaseConnection()

connection.sign_in_as_collector()

for i in range(0, 7):
    try:
        date_input = datetime.now() - timedelta(days=i)
        all_frame = col.get_raw_data(date_input)
        cleaned_data = col.clean_raw_data(all_frame)
        if cleaned_data is not None and not cleaned_data.empty:
            connection.insert_dataframe(frame=cleaned_data, table_name='fic_v3')
    except Exception as e:
        print(e)
