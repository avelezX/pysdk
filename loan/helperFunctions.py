import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia
from utilities.date_functions import datetime_to_ql


class QlHelperFunctions:
    ibr_quantlib_det = {
        'name': 'IBR1D',
        'fixingDays': 1,
        'currency': ql.COPCurrency(),
        'end_of_month': False,
        'calendar': calendar_colombia(),
        'bussiness_convention': ql.Following,
        'dayCounter': ql.Actual360(),
        'settlement_days': 2
    }

    ibr_overnight_index = ql.OvernightIndex(
        ibr_quantlib_det['name'],
        ibr_quantlib_det['fixingDays'],
        ibr_quantlib_det['currency'],
        ibr_quantlib_det['calendar'],
        ibr_quantlib_det['dayCounter']
    )

    def __init__(self):
        pass

    def ibr_swap_cupon_helper(self, rate, tenor, tenor_unit):
        fixedLegFrequency = ql.Quarterly
        fixedLegConvention = self.ibr_quantlib_det['bussiness_convention']
        fixedLegDayCounter = self.ibr_quantlib_det['dayCounter']
        swap = ql.SwapRateHelper(
            rate,
            ql.Period(tenor, tenor_unit),
            self.ibr_quantlib_det['calendar'],
            fixedLegFrequency,
            fixedLegConvention,
            fixedLegDayCounter,
            self.ibr_overnight_index
        )
        return swap

    def depo_helpers_ibr(self, rate, tenor, tenor_unit):
        depo_helper = ql.DepositRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate)),
            ql.Period(tenor, tenor_unit),
            self.ibr_quantlib_det['settlement_days'],
            self.ibr_quantlib_det['calendar'],
            self.ibr_quantlib_det['bussiness_convention'],
            self.ibr_quantlib_det['end_of_month'],
            self.ibr_quantlib_det['dayCounter']
        )

        return depo_helper

    def crear_objeto_curva_ibr(self, quotes, value_date):

        #  TODO La forma de inferir el calendario colombiano interseccion calendario americano
        logLinear = ql.PiecewiseLogLinearDiscount(
            datetime_to_ql(value_date),
            quotes,
            ql.Thirty360(ql.Thirty360.BondBasis)
        )
        return logLinear

    def create_curve(self, db_info, value_date, years):

        OIS_helpers = []

        if db_info is not None:

            if years <= 2:
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_2y'][0] / 100, 24, ql.Months))
            if 2 < years <= 5:
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_2y'][0] / 100, 24, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_5y'][0] / 100, 60, ql.Months))
            if 5 < years <= 10:
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_2y'][0] / 100, 24, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_5y'][0] / 100, 60, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_10y'][0] / 100, 120, ql.Months))
            if 10 < years <= 15:
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_2y'][0] / 100, 24, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_5y'][0] / 100, 60, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_10y'][0] / 100, 120, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_15y'][0] / 100, 180, ql.Months))
            elif years > 15:
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_2y'][0] / 100, 24, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_5y'][0] / 100, 60, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_10y'][0] / 100, 120, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_15y'][0] / 100, 180, ql.Months))
                OIS_helpers.append(self.ibr_swap_cupon_helper(db_info['ibr_20y'][0] / 100, 240, ql.Months))

            OIS_helpers.append(self.depo_helpers_ibr(db_info['ibr_1d'][0] / 100, 1, ql.Days))
            OIS_helpers.append(self.depo_helpers_ibr(db_info['ibr_1m'][0] / 100, 1, ql.Months))
            OIS_helpers.append(self.depo_helpers_ibr(db_info['ibr_3m'][0] / 100, 3, ql.Months))
            OIS_helpers.append(self.depo_helpers_ibr(db_info['ibr_6m'][0] / 100, 6, ql.Months))
            OIS_helpers.append(self.depo_helpers_ibr(db_info['ibr_12m'][0] / 100, 12, ql.Months))

        return self.crear_objeto_curva_ibr(OIS_helpers, value_date)
