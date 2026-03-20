"""
Crypto Daily Price Collector
Fetches daily closing prices from CryptoCompare API and inserts into xerenity.currency table.
Designed to run daily via cron/scheduler.

Data source: https://min-api.cryptocompare.com (no API key required)
"""

from data_collectors.crypto.crypto_compare_collector import CryptoCompareCollector
from db_connection.supabase.Client import SupabaseConnection

# Crypto pairs to collect (FROM:TO)
CRYPTO_PAIRS = [
    ('BTC', 'USD'),
    ('ETH', 'USD'),
    ('SOL', 'USD'),
    ('XRP', 'USD'),
    ('ADA', 'USD'),
    ('DOGE', 'USD'),
    ('AVAX', 'USD'),
    ('DOT', 'USD'),
    ('MATIC', 'USD'),
    ('LINK', 'USD'),
    ('BNB', 'USD'),
    ('LTC', 'USD'),
    ('UNI', 'USD'),
    ('ATOM', 'USD'),
    ('NEAR', 'USD'),
    ('APT', 'USD'),
    ('ARB', 'USD'),
    ('OP', 'USD'),
    ('FTM', 'USD'),
    ('ALGO', 'USD'),
]

DAYS_BACK = 10
TABLE_NAME = 'currency'


def main():
    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    collector = CryptoCompareCollector(name='CryptoCompare')

    for from_symbol, to_symbol in CRYPTO_PAIRS:
        pair_name = f'{from_symbol}:{to_symbol}'

        try:
            print(f'\n🔄 Fetching {pair_name}...')
            data_frame = collector.get_price(
                from_symbol=from_symbol,
                to_symbol=to_symbol,
                history_days=DAYS_BACK
            )

            if len(data_frame) == 0:
                print(f'⚠️  No data for {pair_name}')
                continue

            print(f'✅ Downloaded {len(data_frame)} records for {pair_name}')

            # Check for existing data to avoid duplicates
            last = connection.get_last_by(
                table_name=TABLE_NAME,
                column_name='time',
                filter_by=('currency', pair_name)
            )

            if len(last) > 0:
                filter_date = last[0]['time']
                print(f'🕒 Last record in DB: {filter_date}')
                filtering = data_frame[data_frame['time'] > filter_date].copy(deep=True)
            else:
                print(f'🆕 No existing data, inserting all records.')
                filtering = data_frame.copy(deep=True)

            if filtering.empty:
                print(f'ℹ️  No new data to insert for {pair_name}')
                continue

            # Convert time to string for Supabase insert
            filtering['time'] = filtering['time'].astype(str)

            print(f'⬆️  Inserting {len(filtering)} new records for {pair_name}...')
            connection.insert_dataframe(frame=filtering, table_name=TABLE_NAME)
            print(f'✅ Done: {pair_name}')

        except Exception as e:
            print(f'❌ Error saving {pair_name}: {e}')
            continue

    print('\n✅ Crypto collection complete.')


if __name__ == '__main__':
    main()
