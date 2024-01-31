from db_call.db_call import get_last_banrep_1, get_last_cpi, get_tes_table, get_last_cpi_lag
from bond_functions.tes_quant_lib_details import depo_helpers, tes_quantlib_det
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import pandas as pd
import QuantLib as ql
import datetime as dt
from utilities.date_functions import ql_to_datetime
from bond_functions.bond_curve_structures import BondCurve
from bond_functions.bond_structure import tes_bond_structure
from dotenv import load_dotenv
from src.data_source.tes.tes import Tes
from src.xerenity.xty import Xerenity
import os
import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
load_dotenv()
print(os.getenv('XTY_USER'))
xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

######################################
#  Calculo de curvas implicitas en los TES
######################################


def implied_inflation_calc(central_bank_rate,tes_table,last_cpi):
    central_bank_rate=central_bank_rate/100
    calc_date = ql.Date.todaysDate()
    today = calc_date
    # Traer la tasa del banco central usando el ultimo dato del banrep series.


    print('----------Tasa del banco central------------')
    print(central_bank_rate)

    # TODO actualizar el calendario de politica monetaria para que esta estimacion tenga mas sentido
    depo_maturities = [ql.Period(5, ql.Days), ql.Period(2, ql.Months)]
    depo_rates = [central_bank_rate, central_bank_rate]
    depo_help = depo_helpers(
        depo_maturities, depo_rates, details=tes_quantlib_det)
    # Traer la informacion de los TES activos de la tabla tes
    tes_info = tes_table 

    # Crear la clase bonos para los bonos en COP ( nominales tasa fija)
    cop = BondCurve(currency='COP', country='col',
                    bond_info_df=tes_info, supabase=xty)

    # TODO entrar los tes que estan por omitirse dejarlos por parametro
    # Creando la DF con la informacion de mercado actual de los bonos al momneto de escribir, quisimos quitar los TES24 por distocion de liquidez y los TEV verdes por su iliquidez
    cop_df = cop.create_df(['tes_24', 'tesv_31'])
    print('--------Curva de TES cop actual -------')
    print(cop_df)

    helpers = cop.create_bond_helpers(
        cop_df, excluded_bonds=['tes_24', 'tesv_31'])
    cop_yield_curve = cop.yield_curve_ql(calc_date, helpers, depo_help)

    # TODO Traer ultimo dato de inflacion usando un lag de 12 meses
    inflation_print = last_cpi/100 

    print('----------Tasa de inflacion------------')
    print(central_bank_rate)

    # TODO cambiar por una funcion que calcule los dias al proximo cambio de inflacion
    depo_maturities_uvr = [ql.Period(5, ql.Days), ql.Period(1, ql.Months)]
    uvr_ov_deposit_rate = ((1+central_bank_rate)/(1+inflation_print))-1
    depo_rates_uvr = [uvr_ov_deposit_rate, uvr_ov_deposit_rate]
    depo_help_uvr = depo_helpers(
        depo_maturities_uvr, depo_rates_uvr, details=tes_quantlib_det)
    uvr = BondCurve('UVR', 'col', bond_info_df=tes_info, supabase=xty)
    uvr_df = uvr.create_df()
    print('--------Curva de TES uvr actual -------')
    print(uvr_df)
    helpers_uvr = uvr.create_bond_helpers(uvr_df, excluded_bonds=[])
    uvr_yield_curve = uvr.yield_curve_ql(calc_date, helpers_uvr, depo_help_uvr)

    ######################################
    #  Poniendo las curvas juntas
    ######################################

    end_date = today + ql.Period(10, ql.Years)  # Limit to the next 10 years
    day_count = ql.Actual365Fixed()
    if today.dayOfMonth() < 15:
        init_date = ql.Date(15, today.month(), today.year())

    else:
        init_date = ql.Date(15, today.month(), today.year()
                            )+ql.Period(1, ql.Months)

    dates = [init_date]
    for m in range(1, 121):
        current_date = init_date + ql.Period(m, ql.Months)
        current_date = ql.Date(15, current_date.month(), current_date.year())
        dates.append(current_date)

    # dates = [ql.Date(15, m, y) for y in range(today.year(), end_date.year() + 1) for m in range( if y == today.year() else 1, 13)]

    date_df = pd.DataFrame(data={'Date': dates})

    date_df['Discount Factors'] = date_df['Date'].apply(lambda d: cop_yield_curve.discount(
        d) if cop_yield_curve.timeFromReference(d) <= cop_yield_curve.maxTime() else None)
    date_df['Zero Rates'] = date_df['Date'].apply(lambda d: cop_yield_curve.zeroRate(
        d, day_count, ql.Continuous).rate() if cop_yield_curve.timeFromReference(d) <= cop_yield_curve.maxTime() else None)

    date_df['Discount Factors_UVR'] = date_df['Date'].apply(lambda d: uvr_yield_curve.discount(
        d) if uvr_yield_curve.timeFromReference(d) <= uvr_yield_curve.maxTime() else None)
    date_df['Zero Rates_UVR'] = date_df['Date'].apply(lambda d: uvr_yield_curve.zeroRate(
        d, day_count, ql.Continuous).rate() if uvr_yield_curve.timeFromReference(d) <= uvr_yield_curve.maxTime() else None)
    date_df['Inflacion Implicita'] = (
        (1+date_df['Zero Rates'])/(1+date_df['Zero Rates_UVR'])-1)
    date_df['Date'] = date_df['Date'] - ql.Period('1m')

    df = get_last_cpi_lag()

    df['Total'] = df['indice']
    df['fecha'] = pd.to_datetime(df['fecha'])
    df.set_index('fecha', inplace=True)
    df_cpi = pd.DataFrame(df['Total'].dropna())
    df_cpi.rename(columns={'Total': 'indice'}, inplace=True)
    df_cpi.set_index(pd.to_datetime(df_cpi.index.year*10000 +
                     df_cpi.index.month*100 + 15, format='%Y%m%d'), inplace=True)

    total_cpi = df_cpi['indice']

    print('estoy imprimiendo-----------')
    print(total_cpi)
    for d in date_df['Date']:
        d_1 = d-ql.Period('1y')
        f_1 = total_cpi[ql_to_datetime(d_1)]
        f_2 = (1+date_df['Inflacion Implicita'][date_df['Date'] == d].values)
        total_cpi.loc[ql_to_datetime(d)] = f_1*f_2[0]
        print(d)

    total_cpi = pd.DataFrame(total_cpi)
    total_cpi_monthly = total_cpi.pct_change(periods=1)
    total_cpi_yoy = total_cpi.pct_change(periods=12)


    return {'total_cpi': total_cpi, 'total_cpi_yoy': total_cpi_yoy, 'total_cpi_monthly': total_cpi_monthly}
