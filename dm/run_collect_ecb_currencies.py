from data_collectors.currencies.european_central_bank.ecb_currency_collector import EuropeanCentralBank

from db_connection.supabase.Client import SupabaseConnection

connection = SupabaseConnection()

connection.sign_in_as_collector()

ecb = EuropeanCentralBank(name="CurrencyConvertor")

currencies = ["NOK", "JPY", "CHF", "SEK", "HUF", "PLN", "CNY", "INR", "IDR", "HKD", "MYR", "SGD", "USD", "MXN", "BRL",
              "AUD"]

connection = SupabaseConnection()

connection.sign_in_as_collector()

for from_currency in currencies:

    try:
        data_frame = ecb.get_price(from_symbol=from_currency, history_days=10)

        if len(data_frame) > 0:

            last = connection.get_last_by(table_name='currency', column_name='time',
                                          filter_by=('currency', '{}:{}'.format(from_currency, "EUR")))

            if len(last) > 0:
                filter_date = last[0]['time']
                filtering = data_frame[data_frame['time'] > filter_date].copy(deep=True)
            else:
                filtering = data_frame.copy(deep=True)

            filtering['time'] = filtering['time'].astype(str)

            connection.insert_dataframe(frame=filtering, table_name='currency')
    except Exception as e:
        print('Error saving {}'.format(from_currency))
        print(e)
