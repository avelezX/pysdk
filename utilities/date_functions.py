import QuantLib as ql
import datetime
from scipy.optimize import newton
# Quant Lib realted
def ql_to_string(query_date=ql.Date):
    return '{:02d}/{:02d}/{}'.format(query_date.month(), query_date.dayOfMonth(), query_date.year())

def datetime_to_ql(dt):
    return ql.Date(dt.day, dt.month, dt.year)

def ql_to_datetime(d):
    return datetime.datetime(d.year(), d.month(), d.dayOfMonth())

def add_months(date,months):
    sig= ql.Date(date.day, date.month, date.year) + ql.Period(months,ql.Months)
    sig= ql.Date(sig.dayOfMonth(),sig.month(),sig.year())
    return ql_to_datetime(sig)

def columns_with_date(df):

    def check_column_name(name):
        return 'Date' in name or 'date' in name or 'time' in name or 'Time' in name

    # Identify columns meeting the condition
    return [col for col in df if check_column_name(col)]

def fit_nelson_siegel(x, y):
    def nelson_siegel_curve(t, beta0, beta1, beta2, tau):
        return beta0 + beta1 * ((1 - np.exp(-t / tau)) / (t / tau)) + beta2 * (((1 - np.exp(-t / tau)) / (t / tau)) - np.exp(-t / tau))



# Function to calculate days using ql.Thirty360 (BondBasis)
def days_30_360_ql(start_date, end_date):
    day_count = ql.Thirty360(ql.Thirty360.BondBasis)
    return day_count.dayCount(start_date,end_date)

def days_30_360_dt(start_date, end_date):
    day_count = ql.Thirty360(ql.Thirty360.BondBasis)
    return day_count.dayCount(datetime_to_ql(start_date),datetime_to_ql(end_date))


# Function to calculate days using ql.ActualActual (ISDA)
def days_act_act_ql(start_date, end_date):
    day_count = ql.ActualActual(ql.ActualActual.ISDA)
    return day_count.dayCount(start_date,end_date)

def days_act_act_dt(start_date, end_date):
    day_count = ql.ActualActual(ql.ActualActual.ISDA)
    return day_count.dayCount(datetime_to_ql(start_date),datetime_to_ql(end_date))

# Function to calculate days using ql.Actual365Fixed
def days_act_365_ql(start_date, end_date):
    day_count = ql.Actual365Fixed()
    return day_count.dayCount(start_date,end_date)

def days_act_365_dt(start_date, end_date):
    day_count = ql.Actual365Fixed()
    return day_count.dayCount(datetime_to_ql(start_date),datetime_to_ql(end_date))



# Function to calculate the IRR, NOMINAL ( SYMPLE)
def calculate_irr(dates, cashflows, convention):
    """
    Calculate the Internal Rate of Return (IRR) using the Newton-Raphson method.

    Parameters:
    - dates (list of pd.Timestamp): List of dates for each cash flow
    - cashflows (list of float): List of cash flows corresponding to each date
    - convention (str): Day count convention. One of '30/360', 'actual/actual', or 'actual/365'

    Returns:
    - irr (float): Internal Rate of Return (IRR) in symple convention (tasa nominal)
    """
    def npv(rate, cashflows, dates, convention):
        """Calculate the Net Present Value (NPV) for a given discount rate."""
        start_date = dates[0]
        npv_value = 0
        for cashflow, date in zip(cashflows, dates):
            ql_start = datetime_to_ql(start_date)
            ql_end = datetime_to_ql(date)
            
            if convention == '30/360':
                days = days_30_360_ql(ql_start, ql_end)
                time = days / 360
            elif convention == 'actual/actual':
                days = days_act_act_ql(ql_start, ql_end)
                time = days / 365.25
            elif convention == 'actual/365':
                days = days_act_365_ql(ql_start, ql_end)
                time = days / 365
            else:
                raise ValueError("Unsupported convention. Choose '30/360', 'actual/actual', or 'actual/365'.")
            
            npv_value += cashflow / (1 + rate) ** time
        return npv_value

    # Use Newton's method to find the rate where NPV = 0
    irr_value = newton(lambda r: npv(r, cashflows, dates, convention), x0=0.1)
    return irr_value