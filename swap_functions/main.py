import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import os
from inflation_query.Inflation_query import implied_inflation_calc
from src.xerenity.xty import Xerenity
from utilities.date_functions import add_months,ql_to_datetime
from utilities.rate_conversion_functions import nom_to_effective
from swap_functions.ibr_quantlib_details import ibr_quantlib_det,ibr_overnight_index,ibr_swap_cupon_helper,depo_helpers_ibr
from swap_functions.ibr_swap_ql_functions import ibr_swaps_quotes,crear_objeto_curva_ibr,fwd_rates_generation
from swap_functions.quotes_query import ibr_mean_query,ibr_mean_query_to_dictionary

import pandas as pd
import QuantLib as ql
import plotly.graph_objects as go
from datetime import datetime,date
xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)


############
### Funcion para crear la curva de swaps. 
############


##########
#Traer la serie de IBR swap overnight, en ea. 
ibr_on=xty.BanRep().get_econ_data_last(id_serie=19).data[0]['valor']/100


########
# Ajustando los parametros 

#today=date.today()


##### Cronstruir los datos para el calculo de la curva. 

#####Determinacion del rango de fechas de las cuales se quiere traer los datos de IBR
init_date=datetime(2023, 11, 8).date()
final_date=init_date
start_date=datetime(2023, 12, 15).date()
day_to_avoid_fwd_ois=7
days_to_on=8


def full_ibr_curve_creation(init_date,final_date,day_to_avoid_fwd_ois,days_to_on):
    #####Consulta de datos IBR a Supabase
    ibr_data=pd.DataFrame(xty.get_date_range(table_name='ibr_swaps_cluster',date_column_name='execution_timestamp').data)
    ###Filtramos el Query por los parametros determinados. 
    ibr_cluster_mean=ibr_mean_query(ibr_data,init_date,final_date,day_to_avoid_fwd_swaps=day_to_avoid_fwd_ois)
    ###creacion del directorio para llamarlos como una curva. Esta funcion devuelve in df. 
    ibr_query=ibr_mean_query_to_dictionary(ibr_cluster_mean,'m')


    ########Con el directiorio creamos los helpers en quantlib .to_dict porque recibe una lista de directorios. 
    OIS_helpers=ibr_swaps_quotes(ibr_query.to_dict(orient='records')) 

    #####Poniendole el ON como helper a la curva
    OIS_helpers.append(depo_helpers_ibr(ibr_on,days_to_on,ql.Days)) 

    #### Crendo el objeto curva en la salida. 
    return crear_objeto_curva_ibr(OIS_helpers)


##### Creacion de la curva FWD 

###Creacion de la curva spot
curve=full_ibr_curve_creation(init_date,final_date,day_to_avoid_fwd_ois,days_to_on)

###Creacion de la curva FWD. 
fwd_curve=fwd_rates_generation(curve,start_date,inverval_tenor=3,interval_period='m')

# fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
# print(fwd_curve.to_dict(orient='records'))
fwd_curve.to_clipboard()
fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
print(fwd_curve.to_dict(orient='records'))

#Esto borra todos los datos
xty.session.table('ibr_implicita').delete().not_.is_('fecha', 'null').execute()

# #Creacion de la inflacion implicita en supabase. 
xty.session.table('ibr_implicita').insert(fwd_curve.to_dict(orient='records')).execute()














