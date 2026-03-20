import QuantLib as ql

from data_collectors.DataCollector import DataCollector
from functions_DM.date_func import ql_to_string, ql_timestamp_to_string, time_stamp_to_format
import datetime


class DttcColelctor(DataCollector):

    def __init__(self, name):
        super().__init__(name)

    def payload_historical_dtcc(self, to_date=ql.Date.todaysDate() - 1, from_date=ql.Date.todaysDate(), asset='IR',
                                notional_range=[0, 50e15], currency='COP'):
        return {
            'action': 'historicalSearch',
            'disseminationDateRange.low': ql_to_string(to_date),
            'disseminationDateRange.high': ql_to_string(from_date),
            'jurisdiction': 'CFTC',
            'assetClassification': asset,
            'notionalRange.low': notional_range[0],
            'notionalRange.high': notional_range[1],
            'lowHour': 0,
            'lowMinute': 0,
            'highHour': 23,
            'highMinute': 59,
            'currency': currency,
            'name': "WEBTEST",
            'displayType': 'c'
        }

    def payload_dtcc(self, asset='RATES', notional_range=None, currency='COP',
                     date=datetime.datetime.now()):
        if notional_range is None:
            notional_range = [1, 50000000000000]

        now = date
        body = {
            "jurisdiction": "CFTC",
            "assetClass": asset,
            "currency": currency,
            "minNotionalAmount": notional_range[0],
            "maxNotionalAmount": notional_range[1],
            "displayType": "w",
            "disseminationDateTimeLow": "{}.000Z".format(time_stamp_to_format(
                datetime.datetime(now.year, now.month, now.day, 0, 0, 0),
                "%Y-%m-%dT%H:%M:%S"
            )),
            "disseminationDateTimeHigh": "{}.000Z".format(time_stamp_to_format(
                datetime.datetime(now.year, now.month, now.day, 23, 59, 59),
                "%Y-%m-%dT%H:%M:%S"
            )),
            "productId": None,
            "underlyingAsset": None,
            "upi": None,
            "upiShortName": None,
            "name": None,
            "searchIndicator": "pre"
        }
        return body
