#### Function to filter the information coming from Supabase
import pandas as pd
def ibr_mean_query(ibr_data,init_date,final_date,day_to_avoid_fwd_swaps=7):
    ibr_data['execution_timestamp'] = pd.to_datetime(ibr_data['execution_timestamp']).dt.date
    mask = (ibr_data['execution_timestamp'] >= init_date) & (ibr_data['execution_timestamp'] <= final_date) & (ibr_data['action_type'] == 'NEWT')
    ibr_data = ibr_data[mask] 
    ibr_data= ibr_data[abs(ibr_data['days_diff_trade_effe']) < day_to_avoid_fwd_swaps]
    return  pd.DataFrame(ibr_data.groupby('month_diff_effective_expiration')['rate'].mean())

