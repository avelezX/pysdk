import QuantLib as ql
import datetime

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

