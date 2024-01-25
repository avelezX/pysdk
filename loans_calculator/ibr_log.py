# %%

import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from datetime import datetime
from utilities.date_functions import datetime_to_ql,ql_to_datetime
import pandas as pd
import QuantLib as ql
import pandas as pd
from datetime import datetime
import numpy_financial as npf
import pandas as pd

from swap_functions.main import full_ibr_curve_creation
from loans_calculator.loan_structure import Loan
from db_call.db_call import get_last_n_banrep_ibr_1m_nom,get_last_n_banrep_ibr_3m_nom,get_last_n_banrep_ibr_6m_nom,get_banrep_16

from db_call.db_call import get_banrep_19,get_ibr_cluster_table
db_info={'ibr_cluster_table':get_ibr_cluster_table(),'ibr_on':get_banrep_19(),'ibr_1m':get_banrep_16()}
period_to_curve = { 'SV': get_last_n_banrep_ibr_6m_nom(), 'TV': get_last_n_banrep_ibr_3m_nom(n=365*5), 'MV': get_last_n_banrep_ibr_1m_nom()}

from utilities.colombia_calendar import calendar_colombia

curve_details=full_ibr_curve_creation(desired_date_valuation=ql.Date.todaysDate(),calendar=calendar_colombia(),day_to_avoid_fwd_ois=7,db_info=db_info)
curve=curve_details.crear_curva(days_to_on=1)

dia_creacion=emision = datetime(year=2022, month=12, day=21)
value_date=datetime(year=2024,month=1,day=24)

fix_loan=Loan(interest_rate=5,periodicity='Mensual',number_of_payments=24,start_date=dia_creacion,original_balance=10000,rate_type='FIX',db_info=period_to_curve)
fix_loan.generate_cash_flow_table()


ibr_loan=Loan(interest_rate=5,periodicity='Mensual',number_of_payments=24,start_date=dia_creacion,original_balance=10000,rate_type='IBR',db_info=period_to_curve)
ibr_loan.generate_rates_ibr(value_date=value_date,curve=curve,tipo_de_cobro='por_dias_360',periodicidad_tasa='MV')





