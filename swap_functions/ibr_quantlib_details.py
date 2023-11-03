import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia





ibr_quantlib_det={'name' : 'IBR1D',
                'fixingDays' : 1,
                'currency' : ql.COPCurrency(),
                'calendar' : calendar_colombia(),
                'dayCounter' : ql.Thirty360(ql.Thirty360.BondBasis),
                'settlement_days': 2}

overnight_index = ql.OvernightIndex(ibr_quantlib_det['name'], 
                                    ibr_quantlib_det['fixingDays'],
                                    ibr_quantlib_det['currency'],
                                    ibr_quantlib_det['calendar'],
                                    ibr_quantlib_det['dayCounter'])

