import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import os
from inflation_query.Inflation_query import implied_inflation_calc
from src.xerenity.xty import Xerenity
from utilities.date_functions import add_months
import pandas as pd
import QuantLib as ql
from datetime import datetime
xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

def calculo_serie_uvr(cpi_serie=None):
    if cpi_serie is None:
        cpi_serie=implied_inflation_calc()
    
    indice=cpi_serie
    indice.index = pd.to_datetime(indice.index).date
    uvr=xty.BanRep().get_econ_data_last_n(id_serie=8,n=365*2).data
    uvr=pd.DataFrame(uvr)
    uvr['fecha'] = pd.to_datetime(uvr['fecha'])
    uvr.drop('id_serie', axis=1, inplace=True)
    uvr.set_index('fecha', inplace=True)
    uvr.index = pd.to_datetime(uvr.index).date

    init_date = max(uvr.index)
    for m in range(0, 120):
        current_date = add_months(init_date,m).date()
        next_date=add_months(current_date,1).date()
        try:
            current_index_value=indice.loc[current_date]['indice']
            next_index_value=indice.loc[next_date]['indice']
            valor_uvr=uvr.loc[current_date]['valor']
            uvr.loc[next_date]=valor_uvr*next_index_value/current_index_value
        except:
            print("Existio un error solo se pudo calcular hasta el año")
            print(current_date)
    uvr.dropna().to_csv('uvr_.csv')
    return uvr