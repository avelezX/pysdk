import QuantLib as ql

from data_collectors.DataCollector import DataCollector
from functions_DM.date_func import ql_to_string


class fxDttcColelctor(DataCollector):

    def __init__(self, name):
        super().__init__(name)

    def payload_historical_dtcc(self, to_date=ql.Date.todaysDate() - 1, from_date=ql.Date.todaysDate(), asset='FX',
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

    def payload_dtcc(self, asset='FX', notional_range=[0, 50000000000000], currency='COP'):
        return {
            'action': 'dailySearch',
            'disseminationDateRange.low': ql_to_string(ql.Date.todaysDate()),
            'disseminationDateRange.high': ql_to_string(ql.Date.todaysDate()),
            'jurisdiction': 'CFTC',
            'assetClassification': asset,
            'notionalRange.low': notional_range[0],
            'notionalRange.high': notional_range[1],
            'lowHour': 0,
            'lowMinute': 0,
            'highHour': 23,
            'highMinute': 59,
            'currency': currency,
            'displayType': 'c'
        }
