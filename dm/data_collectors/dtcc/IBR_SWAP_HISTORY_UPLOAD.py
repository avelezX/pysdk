import sys
#sys.path.insert(0,'/Users/avelezxerenity/.pyenv/versions/xerenity/lib/python3.10/site-packages')
sys.path.append('/Users/avelezxerenity/Documents/GitHub/xerenity-dm')
from data_collectors.dtcc.IBR_swap import IBRSwapCollector_historic
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.dtcc.IBR_swap import IBRSwapCollector

col = IBRSwapCollector_historic()
file_path='/Users/avelezxerenity/Documents/GitHub/xerenity-dm/data_collectors/dtcc/IBR2023_CFTC_1638133.csv'

test_1=col.get_raw_data(file_path)
cleaned_data = col.clean_raw_data_1(test_1,columns=col.columns)




connection = SupabaseConnection()

connection.sign_is_as_user(user_name="svelezsaffon@gmail.com", password="Loquita1053778047")

# print(cleaned_data)
connection.insert_dataframe(frame=cleaned_data, table_name='ibr_swaps')