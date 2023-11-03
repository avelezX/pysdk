import QuantLib as ql
from utilities.colombia_calendar import calendar_colombia

# detalles especificos de los TES colombianos en su ajuste en quantlib
tes_quantlib_det={'calc_date':ql.Date.todaysDate(),
    'calendar':calendar_colombia(),
    'bussiness_convention' : ql.Unadjusted,
    'day_count':  ql.Actual36525(),
    'end_of_month' : True,
    'settlement_days' : 0,
    'face_amount': 100,
    'coupon_frequency': ql.Period(ql.Annual),
    'settlement_days' : 0}

#Detalles y creacion de helpers para los depositos de corto plazo en colombia. 
def depo_helpers(depo_mat,depo_rates,details=tes_quantlib_det):
    depo_helper= [ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(r)),
        m,
        tes_quantlib_det['settlement_days'],
        tes_quantlib_det['calendar'],
        tes_quantlib_det['bussiness_convention'],
        tes_quantlib_det['end_of_month'],
        tes_quantlib_det['day_count'] )
        for r, m in zip(depo_rates, depo_mat)]
    return depo_helper


