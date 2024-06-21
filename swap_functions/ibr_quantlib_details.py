import sys

sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia

ibr_quantlib_det = {'name': 'IBR1D',
                    'fixingDays': 1,
                    'currency': ql.COPCurrency(),
                    'end_of_month': False,
                    'calendar': calendar_colombia(),
                    'bussiness_convention': ql.Following,
                    'dayCounter': ql.Actual360(),  # ql.Thirty360(ql.Thirty360.BondBasis),
                    'settlement_days': 2}

ibr_overnight_index = ql.OvernightIndex(ibr_quantlib_det['name'],
                                        ibr_quantlib_det['fixingDays'],
                                        ibr_quantlib_det['currency'],
                                        ibr_quantlib_det['calendar'],
                                        ibr_quantlib_det['dayCounter'])


# Construyendo los rate helpers de los swaps
def ibr_swap_cupon_helper(rate, tenor, tenor_unit):
    fixedLegFrequency = ql.Quarterly
    fixedLegConvention = ibr_quantlib_det['bussiness_convention']
    fixedLegDayCounter = ibr_quantlib_det['dayCounter']
    return ql.SwapRateHelper(rate,
                             ql.Period(tenor, tenor_unit),
                             ibr_quantlib_det['calendar'],
                             fixedLegFrequency,
                             fixedLegConvention,
                             fixedLegDayCounter,
                             ibr_overnight_index)


def depo_helpers_ibr(rate, tenor, tenor_unit):
    depo_helper = ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate)),
                                       ql.Period(tenor, tenor_unit),
                                       ibr_quantlib_det['settlement_days'],
                                       ibr_quantlib_det['calendar'],
                                       ibr_quantlib_det['bussiness_convention'],
                                       ibr_quantlib_det['end_of_month'],
                                       ibr_quantlib_det['dayCounter'])

    return depo_helper

# def ibr_swap_zero_helper(rate,tenor,tenor_unit):
#     settlementDays = ql.Quote
#     fixedLegFrequency = ql.Quarterly
#     fixedLegConvention=ql.Following
#     fixedLegDayCounter = ql.Thirty360(ql.Thirty360.BondBasis)
#     return ql.SwapRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate)),
#                     ql.Period(tenor, tenor_unit),
#                     ibr_quantlib_det['calendar'],
#                     fixedLegFrequency,
#                     fixedLegConvention,
#                     fixedLegDayCounter,
#                     ibr_overnight_index)
