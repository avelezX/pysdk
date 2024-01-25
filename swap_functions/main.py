# %%

import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import os
#from inflation_query.Inflation_query import implied_inflation_calc
from src.xerenity.xty import Xerenity
from utilities.date_functions import add_months,ql_to_datetime
from utilities.colombia_calendar import calendar_colombia
from utilities.rate_conversion_functions import nom_to_effective
from swap_functions.ibr_quantlib_details import ibr_quantlib_det,ibr_overnight_index,ibr_swap_cupon_helper,depo_helpers_ibr
from swap_functions.ibr_swap_ql_functions import ibr_swaps_quotes,crear_objeto_curva_ibr,fwd_rates_generation
from swap_functions.quotes_query import ibr_mean_query,ibr_mean_query_to_dictionary
from db_call.db_call import get_banrep_19,get_ibr_cluster_table,get_banrep_16
import pandas as pd
import QuantLib as ql
import plotly.graph_objects as go
from datetime import datetime,date, time
xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)


############
### Funcion para crear la curva de swaps. 
############

##########
#Traer la serie de IBR swap overnight, en ea. 
#ibr_on=xty.BanRep().get_econ_data_last(id_serie=19).data[0]['valor']/100

db_info={'ibr_cluster_table':get_ibr_cluster_table(),'ibr_on':get_banrep_19(),'ibr_1m':get_banrep_16()}
########
# Ajustando los parametros 
#today=date.today()
##### Cronstruir los datos para el calculo de la curva. 

#####Determinacion del rango de fechas de las cuales se quiere traer los datos de IBR


class full_ibr_curve_creation:
    def __init__(self,desired_date_valuation=ql.Date.todaysDate(),calendar=calendar_colombia(),day_to_avoid_fwd_ois=7,db_info=db_info):
        self.desired_date=desired_date_valuation
        self.calendar=calendar
        # La informacion necesaria para traer de db.
        self.db_info=db_info
        ### Cuantos dias voy a tolerar que el execution date este a distancia del initdate. Esto para saber si es un fwd o un spot 
        self.day_to_avoid_fwd_ois=day_to_avoid_fwd_ois
        # Specify the date for which you want to find the last working day before
        


        # Replace with your desired date
        calendar=calendar_colombia()


        while not calendar.isBusinessDay(self.desired_date):
            desired_date=calendar.advance(self.desired_date,-1,ql.Days)

        def is_past_noon():
            current_time = datetime.now().time()
            noon_time = time(12, 0, 0)  # Noon time
            return current_time >= noon_time

        ### En la tabla de ibrs, desde que dia se quiere traer informacion
        if is_past_noon():
            init_date=ql_to_datetime(self.desired_date) #datetime(2024, 1, 20).date()  
        else:
            init_date=ql_to_datetime(calendar.advance(self.desired_date,-1,ql.Days))
        ### En la Tabla de IBRS hasta que dia se quiere traer informacion. 
        final_date=ql_to_datetime(self.desired_date) #datetime(2024,1,22).date()

        self.init_date=init_date
        self.final_date=final_date

    def crear_curva(self,days_to_on=1):
        #dias para definir el proximo depositod days_to_on=7

        #def full_ibr_curve_creation(init_date,final_date,day_to_avoid_fwd_ois,days_to_on,db_info):
            #####Consulta de datos IBR a Supabase
        ibr_data=pd.DataFrame(db_info['ibr_cluster_table'])
        ibr_data['rate']=ibr_data['rate']/100
        ###Filtramos el Query por los parametros determinados. 
        ibr_cluster_mean=ibr_mean_query(ibr_data,self.init_date,self.final_date,day_to_avoid_fwd_swaps=self.day_to_avoid_fwd_ois)
        ###creacion del directorio para llamarlos como una curva. Esta funcion devuelve in df. 
        ibr_query=ibr_mean_query_to_dictionary(ibr_cluster_mean,'m')
        ########Con el directiorio creamos los helpers en quantlib .to_dict porque recibe una lista de directorios. 
        OIS_helpers=ibr_swaps_quotes(ibr_query.to_dict(orient='records')) 
        ### Variable para ponerle una maduiracion a los depositos. 
        
        #####Poniendole el ON como helper a la curva
        print('depo helper info:')
        print('rate:')
        print(db_info['ibr_1m'])
        print('tenor:')
        print(days_to_on)
        OIS_helpers.append(depo_helpers_ibr(db_info['ibr_1m'],days_to_on,ql.Months)) 
        #### Crendo el objeto curva en la salida. 
        curve= crear_objeto_curva_ibr(OIS_helpers)
        return curve

##### Creacion de la curva FWD 
###Creacion de la curva spot
#curve=full_ibr_curve_creation(init_date,final_date,day_to_avoid_fwd_ois,days_to_on,db_info=db_info)
#Que dia quiero empezar el FWD day calculation
curve_details=full_ibr_curve_creation(desired_date_valuation=ql.Date.todaysDate(),calendar=calendar_colombia(),day_to_avoid_fwd_ois=7,db_info=db_info)

start_date=ql_to_datetime(curve_details.desired_date)    
###Creacion de la curva FWD. 
curve=curve_details.crear_curva(days_to_on=1)
fwd_curve=fwd_rates_generation(curve,start_date,inverval_tenor=3,interval_period='m')
### Publicacion de la curva FWD. 

fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
def nom_to_effective(nominal_rate,compounding_frequency):
    return (1 + nominal_rate / compounding_frequency) ** compounding_frequency - 1
fwd_curve['rate']=nom_to_effective(fwd_curve['rate'],365)*100
print(fwd_curve.to_dict(orient='records'))

#Esto borra todos los datos
xty.session.table('ibr_implicita').delete().not_.is_('fecha', 'null').execute()

# #Creacion de la inflacion implicita en supabase. 
xty.session.table('ibr_implicita').insert(fwd_curve.to_dict(orient='records')).execute()















# %%
