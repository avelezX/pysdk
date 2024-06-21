#### Function to filter the information coming from Supabase
import pandas as pd


def ibr_mean_query(ibr_data, init_date, final_date, day_to_avoid_fwd_swaps=7):
    init_date = pd.to_datetime(init_date).date()
    final_date = pd.to_datetime(final_date).date()
    ibr_data['execution_timestamp'] = pd.to_datetime(ibr_data['execution_timestamp']).dt.date
    mask = (ibr_data['execution_timestamp'] >= init_date) & (ibr_data['execution_timestamp'] <= final_date) & (
                ibr_data['action_type'] == 'NEWT')
    ibr_data = ibr_data[mask]

    ibr_data = ibr_data[abs(ibr_data['days_diff_trade_effe']) < day_to_avoid_fwd_swaps]
    return pd.DataFrame(ibr_data.groupby('month_diff_effective_expiration')['rate'].mean())


def ibr_mean_query_to_dictionary(ibr_query, tenor_unit):
    ibr_query['tenor_unit'] = tenor_unit
    ibr_query = ibr_query.reset_index()
    ibr_query.rename(columns={'month_diff_effective_expiration': 'tenor'}, inplace=True)
    return ibr_query.reset_index()

def ibr_query():
    pass