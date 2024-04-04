# %%
import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
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
from db_call.db_call import get_last_banrep_8,get_tes_table,get_last_banrep_1,get_last_cpi,get_banrep_19, get_ibr_cluster_table, get_banrep_16




xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

# Necesarias para la creacion diaria de las curvas. 
db_info = {'ibr_cluster_table': get_ibr_cluster_table(), 'ibr_on': get_banrep_19(), 'ibr_1m': get_banrep_16()}


#############################################
####### Generacion de la curva de IBR  ######
#############################################
# Creacion de la curva FWD
# Creacion de la curva spot
curve_details = full_ibr_curve_creation(desired_date_valuation=ql.Date.todaysDate(), calendar=calendar_colombia(), day_to_avoid_fwd_ois=7, db_info=db_info)
start_date = ql_to_datetime(curve_details.desired_date)
# Creacion de la curva FWD.
curve = curve_details.crear_curva(days_to_on=1)
fwd_curve = fwd_rates_generation(curve, start_date, inverval_tenor=3, interval_period='m')
# Publicacion de la curva FWD.
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
# fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))
fwd_curve['rate'] = fwd_curve['rate']*100
xty.session.table('ibr_implicita').delete().not_.is_('fecha', 'null').execute()
# Creacion de la inflacion implicita en supabase.
xty.session.table('ibr_implicita').insert(fwd_curve.to_dict(orient='records')).execute()




#############################################
####### Generacion de UBR  ######
#############################################

today =start_date #datetime(202, 1, 31)
db_uvr_call={'uvr':get_last_banrep_8(),'cbr':get_last_banrep_1(),'tes_table':get_tes_table(),'last_cpi':get_last_cpi()}

# Calculate the vectors

cpi = implied_inflation_calc(db_uvr_call['cbr'],db_uvr_call['tes_table'],db_uvr_call['last_cpi'])
uvr_projec = calculo_serie_uvr(cpi_serie=cpi['total_cpi'],uvr_db=db_uvr_call['uvr'])



# uvr_projec.reset_index(inplace=True)
# uvr_projec.rename(columns={'index': 'fecha'}, inplace=True)
# uvr_projec.reset_index(drop=True, inplace=True)
# uvr_projec['fecha'] = uvr_projec['fecha'].astype(str)


xty.session.table('uvr_projection').delete().not_.is_(
    'fecha', 'null').execute()
xty.session.table('uvr_projection').insert(
    uvr_projec.to_dict(orient='records')).execute()

# uvr_proyec.to_clipboard()
# cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})

# xty.session.table('inflacion_implicita').insert(cpi['total_cpi'].to_dict(orient='records')).execute()

cpi = cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})
cpi['fecha'] = pd.to_datetime(cpi['fecha']).apply(str)
print(cpi.to_dict(orient='records'))

# Esto borra todos los datos
xty.session.table('inflacion_implicita').delete().not_.is_(
    'fecha', 'null').execute()
# Creacion de la inflacion implicita en supabase.
xty.session.table('inflacion_implicita').insert(
    cpi.to_dict(orient='records')).execute()

# %%
