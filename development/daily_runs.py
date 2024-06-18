# %%
import sys

#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
sys.path.append("/Users/andre/Documents/xerenity/pysdk")
import os
import pandas as pd
from src.xerenity.xty import Xerenity
import QuantLib as ql
from utilities.date_functions import ql_to_datetime
from utilities.colombia_calendar import calendar_colombia
from swap_functions.ibr_swap_ql_functions import fwd_rates_generation
from swap_functions.main import full_ibr_curve_creation
from inflation_query.uvr_calc import calculo_serie_uvr
from inflation_query.Inflation_query import implied_inflation_calc
from db_call.db_call import get_tes_table, get_last_cpi, get_ibr_cluster_table, get_last_banrep

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

# Necesarias para la creacion diaria de las curvas. 


initial_date = '2024-06-11 00:00:00'
final_date = '2024-06-12 19:17:34'

ibr_cluster_table = get_ibr_cluster_table(initial_date=initial_date, final_date=final_date)
db_info = {'ibr_cluster_table': get_ibr_cluster_table(initial_date=initial_date, final_date=final_date),
           'ibr_on': get_last_banrep("Indicador Bancario de Referencia (IBR) overnight, nominal", 0).data[0][
                         'valor'] / 100,
           'ibr_1m': get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal", 365 * 5).data[0][
                         'valor'] / 100,
           'ibr_3m': get_last_banrep("Indicador Bancario de Referencia (IBR) 3 Meses, nominal", 365 * 5).data[0][
                         'valor'] / 100,
           'ibr_6m': get_last_banrep("Indicador Bancario de Referencia (IBR) 6 Meses, nominal", 365 * 5).data[0][
                         'valor'] / 100,
           'ibr_12m': get_last_banrep("Indicador Bancario de Referencia (IBR) 12 Meses, efectiva", 365 * 5).data[0][
                          'valor'] / 100,
           }

#############################################
####### Generacion de la curva de IBR  ######
#############################################
# Creacion de la curva FWD
# Creacion de la curva spot
curve_details = full_ibr_curve_creation(desired_date_valuation=ql.Date.todaysDate(),
                                        calendar=calendar_colombia(),
                                        day_to_avoid_fwd_ois=7,
                                        db_info=db_info)

start_date = ql_to_datetime(curve_details.desired_date)
# Creacion de la curva FWD.
curve = curve_details.crear_curva(days_to_on=1)

curve_info = curve["info"]
curve = curve["objeto"]

#############################################################
#############IMprime la curva como queda en los helpers######
#############################################################

# Assuming 'curve_info' is your list of RateHelper objects
# curve_info = [...]

# Initialize list to store dates and quotes as tuples
date_quote_pairs = []

# Iterate over each RateHelper to extract the relevant information
for helper in curve_info:
    # Extract the maturity date
    maturity_date = helper.latestDate()

    # Extract the quote (rate)
    quote_handle = helper.quote()
    quote = quote_handle.value()

    # Append the (date, quote) tuple to the list
    date_quote_pairs.append((maturity_date, quote))

# Sort the list by date
date_quote_pairs.sort(key=lambda x: x[0])

# Print out the dates and corresponding quotes
print("Dates and Quotes from Rate Helpers (sorted by date):")
for date, quote in date_quote_pairs:
    print(f"Date: {date}, Quote: {quote:.6%}")

###########################################################
###########################################################
#############################################################


# %%


# Curva 1m fwd ####################
fwd_curve = fwd_rates_generation(curve, start_date, inverval_tenor=1, interval_period='m')
# Publicacion de la curva FWD.
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
# fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))
fwd_curve['rate'] = fwd_curve['rate'] * 100
xty.session.table('ibr_implicita_1m').delete().not_.is_('fecha', 'null').execute()
xty.session.table('ibr_implicita_1m').insert(fwd_curve.to_dict(orient='records')).execute()
# Creacion de la inflacion implicita en supabase.


# Curva 3m fwd ####################
fwd_curve = fwd_rates_generation(curve, start_date, inverval_tenor=3, interval_period='m')
# Publicacion de la curva FWD.
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
# fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))
fwd_curve['rate'] = fwd_curve['rate'] * 100
xty.session.table('ibr_implicita_3m').delete().not_.is_('fecha', 'null').execute()
xty.session.table('ibr_implicita_3m').insert(fwd_curve.to_dict(orient='records')).execute()
# Creacion de la inflacion implicita en supabase.

# Curva 6m fwd ####################
fwd_curve = fwd_rates_generation(curve, start_date, inverval_tenor=6, interval_period='m')
# Publicacion de la curva FWD.
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
# fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))
fwd_curve['rate'] = fwd_curve['rate'] * 100
xty.session.table('ibr_implicita_6m').delete().not_.is_('fecha', 'null').execute()
xty.session.table('ibr_implicita_6m').insert(fwd_curve.to_dict(orient='records')).execute()
# Creacion de la inflacion implicita en supabase.


# Curva 12m fwd ####################
fwd_curve = fwd_rates_generation(curve, start_date, inverval_tenor=12, interval_period='m')
# Publicacion de la curva FWD.
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
# fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))
fwd_curve['rate'] = fwd_curve['rate'] * 100
xty.session.table('ibr_implicita_12m').delete().not_.is_('fecha', 'null').execute()
xty.session.table('ibr_implicita_12m').insert(fwd_curve.to_dict(orient='records')).execute()
# Creacion de la inflacion implicita en supabase.


# %%


# %%
