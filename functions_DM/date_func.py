import QuantLib as ql
import datetime


# Quant Lib realted
def ql_to_string(query_date=ql.Date):
    return '{:02d}/{:02d}/{}'.format(query_date.month(), query_date.dayOfMonth(), query_date.year())


def datetime_to_ql(dt):
    return ql.Date(dt.day, dt.month, dt.year)


def ql_to_datetime(d):
    return datetime.datetime(d.year(), d.month(), d.dayOfMonth())


def time_stamp_to_format(stamp, format):
    return stamp.strftime(format)


def ql_timestamp_to_string(query_date=ql.Date):
    # 2024-01-29T00:00:00.000Z
    date = time_stamp_to_format(ql_to_datetime(query_date),"%Y-%m-%d")
    return str(date)
