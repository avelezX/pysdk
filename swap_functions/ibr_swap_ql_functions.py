import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import os
from inflation_query.Inflation_query import implied_inflation_calc
from src.xerenity.xty import Xerenity
from utilities.date_functions import add_months,ql_to_datetime,datetime_to_ql
from swap_functions.ibr_quantlib_details import ibr_quantlib_det,ibr_overnight_index,ibr_swap_cupon_helper,depo_helpers_ibr
from global_definitions.dates_mgt import  dates_convention_to_ql
import pandas as pd
import QuantLib as ql
import plotly.graph_objects as go
from datetime import datetime,date
xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

###################
## BIG TODO la curva tiene ql.Actual360. Esta deberia ser 



####################################
####---Creating the IBR swaps helpers
####################################
###

# Create the helpers ( qutes) in the quantlib library.
#Input a dictionary with the keys rate, tenor and tenor_unit
def ibr_swaps_quotes(ibr_quotes):

    OIS_helpers = []
    for quote in ibr_quotes:
        print(quote)

        if ql.Period(quote['tenor'],dates_convention_to_ql[quote['tenor_unit']])<=ql.Period(18,ql.Months):
            OIS_helpers.append(depo_helpers_ibr(quote['rate'],quote['tenor'],dates_convention_to_ql[quote['tenor_unit']]))

        else:
            OIS_helpers.append( ibr_swap_cupon_helper(quote['rate'],quote['tenor'],dates_convention_to_ql[quote['tenor_unit']]))

    return OIS_helpers
  
# TODO el usuario deberia poder cambiar el tipo de curva creada en ql por otro tipo de 
# Create the quantlib curve. 
def crear_objeto_curva_ibr(quotes):
    return ql.PiecewiseSplineCubicDiscount(0, ibr_quantlib_det['calendar'], quotes, ql.Actual360())






def fwd_rates_generation(curve,start_date,inverval_tenor=3,interval_period='m'):

    # Initialize lists to store results
    dates = []
    forward_rates = []
    # Loop through 1-year steps up to 10 years (120 months)
    for i in range(1, 119):
        try:
        # Calculate the forward rate for the current step
            first_date = datetime_to_ql(start_date) + ql.Period(i, dates_convention_to_ql[interval_period])
            end_date = first_date + ql.Period(inverval_tenor, dates_convention_to_ql[interval_period])
            forward_rate = curve.forwardRate(first_date, end_date, ql.Actual360(), ql.Compounded).rate()
            dates.append(first_date)
            forward_rates.append(forward_rate)
            # Print the result
            #print(f"1-month {i/12} year forward rate: {forward_rate:.4%}")
        except:
            
            print('fwd curve tenor to calculate not in curve quotes')

    df = pd.DataFrame(list(zip(dates, forward_rates)), columns=['Maturity Date', 'rate'])
    df['Maturity Date'] = df['Maturity Date'].apply(ql_to_datetime)
    df.set_index('Maturity Date', inplace=True)
    return df
    
