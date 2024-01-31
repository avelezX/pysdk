# %%
import sys,os
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from swap_functions.main import full_ibr_curve_creation
from swap_functions.ibr_swap_ql_functions import fwd_rates_generation
from utilities.colombia_calendar import calendar_colombia
from utilities.date_functions import ql_to_datetime
import QuantLib as ql
from src.xerenity.xty import Xerenity
import pandas as pd
from db_call.db_call import get_banrep_19,get_ibr_cluster_table,get_banrep_16

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

#### Creacion de la curva FWD 
##Creacion de la curva spot
db_info={'ibr_cluster_table':get_ibr_cluster_table(),'ibr_on':get_banrep_19(),'ibr_1m':get_banrep_16()}

curve_details=full_ibr_curve_creation(desired_date_valuation=ql.Date.todaysDate(),calendar=calendar_colombia(),day_to_avoid_fwd_ois=7,db_info=db_info)

start_date=ql_to_datetime(curve_details.desired_date)

##Creacion de la curva FWD. 
curve=curve_details.crear_curva(days_to_on=1)
fwd_curve=fwd_rates_generation(curve,start_date,inverval_tenor=3,interval_period='m')
## Publicacion de la curva FWD. 

fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)




# def nom_to_effective(nominal_rate,compounding_frequency):
#    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1

#fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
# print(fwd_curve.to_dict(orient='records'))

#Esto borra todos los datos
fwd_curve['rate']=fwd_curve['rate']*100
xty.session.table('ibr_implicita').delete().not_.is_('fecha', 'null').execute()

#Creacion de la inflacion implicita en supabase. 
xty.session.table('ibr_implicita').insert(fwd_curve.to_dict(orient='records')).execute()
