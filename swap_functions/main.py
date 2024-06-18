from utilities.date_functions import ql_to_datetime
from utilities.colombia_calendar import calendar_colombia

from swap_functions.ibr_quantlib_details import depo_helpers_ibr
from swap_functions.ibr_swap_ql_functions import ibr_swaps_quotes, crear_objeto_curva_ibr
from swap_functions.quotes_query import ibr_mean_query, ibr_mean_query_to_dictionary

import pandas as pd
import QuantLib as ql

from datetime import datetime, time


class full_ibr_curve_creation:

    def is_past_noon(self):
        current_time = datetime.now().time()
        noon_time = time(12, 0, 0)  # Noon time
        return False  # current_time >= noon_time

    def __init__(self, desired_date_valuation=ql.Date.todaysDate(),
                 calendar=calendar_colombia(),
                 day_to_avoid_fwd_ois=7, db_info=None):
        self.desired_date = desired_date_valuation
        self.calendar = calendar
        # La informacion necesaria para traer de db.
        self.db_info = db_info
        # Cuantos dias voy a tolerar que el execution date este a distancia del initdate. Esto para saber si es un fwd o un spot
        self.day_to_avoid_fwd_ois = day_to_avoid_fwd_ois
        # Specify the date for which you want to find the last working day before

        while not calendar.isBusinessDay(self.desired_date):
            self.desired_date = calendar.advance(
                self.desired_date, -1, ql.Days)

        # En la tabla de ibrs, desde que dia se quiere traer informacion
        if self.is_past_noon():
            # datetime(2024, 1, 20).date()
            init_date = ql_to_datetime(self.desired_date)
        #TODO !!! Quitar el Quedamo de estos dias. 
        else:
            init_date = ql_to_datetime(
                calendar.advance(self.desired_date, 0, ql.Days))
        # En la Tabla de IBRS hasta que dia se quiere traer informacion.
        # datetime(2024,1,22).date()
        final_date = ql_to_datetime(self.desired_date)

        self.init_date = init_date
        self.final_date = final_date

    def crear_curva(self, days_to_on=1):

        # dias para definir el proximo depositod days_to_on=7

        # def full_ibr_curve_creation(init_date,final_date,day_to_avoid_fwd_ois,days_to_on,db_info):
        # Consulta de datos IBR a Supabase

        ibr_data = pd.DataFrame(self.db_info['ibr_cluster_table'])
        ibr_data['rate'] = ibr_data['rate'] / 100

        # Filtramos el Query por los parametros determinados.
        ibr_cluster_mean = ibr_mean_query(
            ibr_data,
            self.init_date,
            self.final_date,
            day_to_avoid_fwd_swaps=self.day_to_avoid_fwd_ois)
        # creacion del directorio para llamarlos como una curva. Esta funcion devuelve in df.

        ibr_query = ibr_mean_query_to_dictionary(ibr_cluster_mean, 'm')
        # Con el directiorio creamos los helpers en quantlib .to_dict porque recibe una lista de directorios.

        OIS_helpers = ibr_swaps_quotes(ibr_query.to_dict(orient='records'))

        # Variable para ponerle una maduracion a los depositos.
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_1m'], 1, ql.Months))
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_3m'], 3, ql.Months))
        # OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_6m'], 6, ql.Months))
        # OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_12m'], 12, ql.Months))
        # Crendo el objeto curva en la salida.
        # curve= crear_objeto_curva_ibr(OIS_helpers)
        return {"objeto": crear_objeto_curva_ibr(OIS_helpers), "info": OIS_helpers}

# %%
