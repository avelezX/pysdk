import sys

sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import os
# from inflation_query.Inflation_query import implied_inflation_calc

from utilities.date_functions import add_months, ql_to_datetime, datetime_to_ql
from swap_functions.ibr_quantlib_details import ibr_quantlib_det, ibr_overnight_index, ibr_swap_cupon_helper, \
    depo_helpers_ibr
from global_definitions.dates_mgt import dates_convention_to_ql
import pandas as pd
import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia

from datetime import datetime, date

# xty = Xerenity(
#    username=os.getenv('XTY_USER'),
#    password=os.getenv('XTY_PWD'),
# )

###################
## BIG TODO la curva tiene ql.Actual360. Esta deberia ser 


####################################
####---Creating the IBR swaps helpers
####################################
###

# Create the helpers ( qutes) in the quantlib library.
# Input a dictionary with the keys rate, tenor and tenor_unit

calendar_colombia = calendar_colombia()


def ibr_swaps_quotes(ibr_quotes):
    OIS_helpers = []
    for quote in ibr_quotes:

        if ql.Period(quote['tenor'], dates_convention_to_ql[quote['tenor_unit']]) <= ql.Period(18, ql.Months):
            OIS_helpers.append(
                depo_helpers_ibr(quote['rate'], quote['tenor'], dates_convention_to_ql[quote['tenor_unit']]))

        else:
            OIS_helpers.append(
                ibr_swap_cupon_helper(quote['rate'], quote['tenor'], dates_convention_to_ql[quote['tenor_unit']]))

    return OIS_helpers


# TODO el usuario deberia poder cambiar el tipo de curva creada en ql por otro tipo de 
# Create the quantlib curve. 
def crear_objeto_curva_ibr(quotes):
    # return ql.PiecewiseSplineCubicDiscount(0, ibr_quantlib_det['calendar'], quotes, ql.Actual360())
    return ql.PiecewiseLogLinearDiscount(0, ibr_quantlib_det['calendar'], quotes, ql.Actual360())


def fwd_rates_generation(curve, start_date, inverval_tenor=3, interval_period='m'):
    # Initialize lists to store results
    dates = []
    forward_rates = []
    # Loop through 1-year steps up to 10 years (120 months)
    first_date = datetime_to_ql(start_date)

    first_date = calendar_colombia.advance(datetime_to_ql(start_date), 1, ql.Days)

    for i in range(1, 365 * 5):
        try:
            # Calculate the forward rate for the current step
            # i=1
            # interval_period='m'
            # inverval_tenor=3

            end_date = first_date + ql.Period(inverval_tenor, dates_convention_to_ql[interval_period])
            forward_rate = curve.forwardRate(first_date, end_date, ql.Actual360(), ql.Simple).rate()
            dates.append(first_date)
            forward_rates.append(forward_rate)

            first_date = calendar_colombia.advance(datetime_to_ql(start_date), i, ql.Days)

        # first_date = datetime_to_ql(start_date) + ql.Period(i, ql.Days)
        # Print the result
        # print(f"1-month {i/12} year forward rate: {forward_rate:.4%}")
        except Exception as e:
            print(e)

    df = pd.DataFrame(list(zip(dates, forward_rates)), columns=['Maturity Date', 'rate'])
    df['Maturity Date'] = df['Maturity Date'].apply(ql_to_datetime)
    df.set_index('Maturity Date', inplace=True)
    return df
