import sys
#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
sys.path.append("/Users/andre/Documents/xerenity/pysdk")


from db_call.db_call import get_last_banrep,get_ibr_cluster_table
from loans_calculator.loan_structure import Loan



from datetime import datetime
from datetime import date
import pandas as pd
import QuantLib as ql
from swap_functions.main import full_ibr_curve_creation
from utilities.colombia_calendar import calendar_colombia
import json


periodicity="Mensual"
interest_rate=3.51
periodicity="Mensual"
number_of_payments=12
datetime_date="2022-04-12"
start_date=datetime.strptime(datetime_date, '%Y-%m-%d')
original_balance=600*1000000
rate_type='IBR'
days_count='por_dias_365' #'por_periodo'#'por_dias_360'
grace_type=None
grace_period=None
min_period_rate=12


SV=get_last_banrep("Indicador Bancario de Referencia (IBR) 6 Meses, nominal",365*5).data
initial_date='2024-06-17 00:00:00'
final_date='2024-06-17 19:17:34'

ibr_cluster_table=get_ibr_cluster_table(initial_date=initial_date,final_date=final_date)
TV=get_last_banrep("Indicador Bancario de Referencia (IBR) 3 Meses, nominal",365*5).data
MV=get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal",365*5).data
ibr_1m=get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal").data[0]['valor']
ibr_3m=get_last_banrep("Indicador Bancario de Referencia (IBR) 3 Meses, nominal").data[0]['valor']
db_info={'SV': SV,
        'ibr_cluster_table': ibr_cluster_table,
        'TV': TV,
        'MV': MV,
        'ibr_1m': ibr_1m/100,
        'ibr_3m':ibr_3m/100
        }

calc=Loan(interest_rate=interest_rate,
          periodicity=periodicity,
          number_of_payments=number_of_payments,
          start_date=start_date,
          original_balance=original_balance,
          rate_type=rate_type,
          days_count=days_count,
          grace_type=grace_type,
          grace_period=grace_period,
          db_info=db_info,
          min_period_rate=min_period_rate
          )

calc.rate_type = 'IBR'
today = datetime.today().date()
start = ql.Date(today.day, today.month, today.year)
ql_today = ql.Date(today.day, today.month, today.year)
calendar = calendar_colombia()
depth_search = 8

while not calendar.isBusinessDay(start) and depth_search >= 0:
    start = calendar.advance(start, -1, ql.Days)
    depth_search = depth_search - 1

if depth_search == 0:
    print("No business day found in {} days".format(depth_search))
    start = ql_today

value_date = datetime(year=start.year(), month=start.month(), day=start.dayOfMonth())

curve_details = full_ibr_curve_creation(
    desired_date_valuation=ql.Date(value_date.day, value_date.month, value_date.year),
    calendar=calendar_colombia(),
    day_to_avoid_fwd_ois=7,
    db_info=calc.db_info
)

curve = curve_details.crear_curva(days_to_on=1)["objeto"]

curve_details.crear_curva(days_to_on=1)['info']

payment = calc.generate_rates_ibr(
    value_date=value_date,
    curve=curve)

payment.to_clipboard()
