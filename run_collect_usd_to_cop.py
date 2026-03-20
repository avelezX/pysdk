from datetime import datetime, timedelta
from db_connection.supabase.Client import SupabaseConnection
from data_collectors.currencies.usd_cop.usd_to_cop_collector import UsToCopCollector

collector = UsToCopCollector(name='USD:COP')

from_date = datetime.today()

days = 1

apply_filtering = True

for x in range(0, days):

    search_date = from_date - timedelta(days=x)

    data_frame = collector.get_stock_price(from_date=search_date, symbol=collector.name)

    if len(data_frame) > 0:
        connection = SupabaseConnection()

        connection.sign_in_as_collector()

        last = connection.get_last_by(table_name='currency_hour', column_name='time', filter_by=('currency', collector.name))

        print('Saving {} from {}'.format(collector.name, last))

        if apply_filtering and len(last) > 0:
            filter_date = last[0]['time']
            filtering = data_frame[data_frame['time'] > filter_date].copy(deep=True)
        else:
            filtering = data_frame.copy(deep=True)

        filtering['time'] = filtering['time'].astype(str)

        connection.insert_dataframe(frame=filtering, table_name='currency_hour')
