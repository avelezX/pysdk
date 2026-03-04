
# %%
# LEGACY SCRIPT — kept as historical reference only.
#
# This script was written against a no-longer-available internal SDK and
# a removed module (swap_functions/main.py).  It is NOT runnable as-is.
#
# Migration notes:
#   - Replace `from db_call.db_call import ...`
#       with MarketDataLoader from pricing.data.market_data
#       (or query Supabase directly via the Management API).
#   - Replace `full_ibr_curve_creation` (swap_functions.main — removed)
#       with `build_ibr_curve` from pricing.curves.ibr_curve:
#
#           from pricing.curves.ibr_curve import build_ibr_curve
#           curve, quotes = build_ibr_curve(db_info, valuation_date)
#
#   - `loans_calculator.loan_structure.Loan` has been superseded by
#       `loan.Loan` and `loan.ibrLoan.IbrLoan`.

import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import QuantLib as ql
from datetime import datetime
from utilities.colombia_calendar import calendar_colombia

# --- BROKEN IMPORTS (legacy) ---
# from swap_functions.main import full_ibr_curve_creation   # module removed
# from loans_calculator.loan_structure import Loan           # legacy path
# from db_call.db_call import get_last_banrep               # legacy SDK
# from db_call.db_call import get_ibr_cluster_table, get_last_banrep  # legacy SDK

# --- REPLACEMENT (use these instead) ---
# from pricing.curves.ibr_curve import build_ibr_curve
# from loan.ibrLoan import IbrLoan

# db_info = { ... }  # populate via MarketDataLoader or direct Supabase query
# curve, quotes = build_ibr_curve(db_info, valuation_date=ql.Date.todaysDate())

# --- LEGACY CODE (not runnable — kept for reference) ---
# db_info = {'ibr_cluster_table': get_ibr_cluster_table(),
#            'ibr_on': get_last_banrep("Indicador Bancario de Referencia (IBR) overnight, nominal", 0) / 100,
#            'ibr_1m': get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal", 365 * 5).data[0]['valor'] / 100}
# period_to_curve = {
#     'SV': get_last_banrep("Indicador Bancario de Referencia (IBR) 6 Meses, nominal", 365 * 5).data,
#     'TV': get_last_banrep("Indicador Bancario de Referencia (IBR) 3 Meses, nominal", 365 * 5).data,
#     'MV': get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal", 365 * 5).data,
#     'ibr_cluster_table': get_ibr_cluster_table(),
#     'ibr_on': get_last_banrep("Indicador Bancario de Referencia (IBR) overnight, nominal", 0) / 100,
#     'ibr_1m': get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal", 365 * 5).data[0]['valor'] / 100,
# }

# curve_details = full_ibr_curve_creation(
#     desired_date_valuation=ql.Date.todaysDate(),
#     calendar=calendar_colombia(),
#     day_to_avoid_fwd_ois=7,
#     db_info=db_info,
# )
# curve = curve_details.crear_curva(days_to_on=1)

# dia_creacion = emision = datetime(year=2022, month=12, day=21)
# value_date = datetime(year=2024, month=1, day=24)

# fix_loan = Loan(interest_rate=5, periodicity='Mensual', number_of_payments=24, start_date=dia_creacion,
#                 original_balance=10000, rate_type='FIX', db_info=period_to_curve)
# fix_loan.generate_cash_flow_table()

# ibr_loan = Loan(interest_rate=5, periodicity='Mensual', number_of_payments=24, start_date=dia_creacion,
#                 original_balance=10000, rate_type='IBR', db_info=period_to_curve)
# ibr_loan.generate_rates_ibr(value_date=value_date, curve=curve, tipo_de_cobro='por_dias_360', periodicidad_tasa='MV')

# %%
