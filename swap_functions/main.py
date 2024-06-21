from utilities.date_functions import ql_to_datetime
from utilities.colombia_calendar import calendar_colombia

from swap_functions.ibr_quantlib_details import depo_helpers_ibr,ibr_swap_cupon_helper
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

        final_date = ql_to_datetime(self.desired_date)

        self.final_date = final_date

    def crear_curva(self, days_to_on=1):

        OIS_helpers = []

        OIS_helpers.append(ibr_swap_cupon_helper(self.db_info['ibr_2y'][0]/100, 24, ql.Months))
        OIS_helpers.append(ibr_swap_cupon_helper(self.db_info['ibr_5y'][0]/100, 60, ql.Months))
        OIS_helpers.append(ibr_swap_cupon_helper(self.db_info['ibr_10y'][0]/100, 120, ql.Months))

        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_1d'][0]/100, 1, ql.Days))
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_1m'][0]/100, 1, ql.Months))
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_3m'][0]/100, 3, ql.Months))
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_6m'][0]/100, 6, ql.Months))
        OIS_helpers.append(depo_helpers_ibr(self.db_info['ibr_12m'][0]/100, 12, ql.Months))

        return {"objeto": crear_objeto_curva_ibr(OIS_helpers), "info": OIS_helpers}

# %%
