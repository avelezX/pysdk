
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
from db_call.db_call import get_tes_table,get_last_cpi, get_ibr_cluster_table,get_last_banrep


xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)


start_date=ql.Date.todaysDate()

#############################################
####### Generacion de UVR  ######
#############################################

today =start_date #datetime(202, 1, 31)
db_uvr_call={'uvr':get_last_banrep("Unidad de Valor Real (UVR)",n=365*2).data,  
             'cbr':get_last_banrep("Tasa de Politica Monetaria",0).data[0]['valor'],
             'tes_table':get_tes_table(),'last_cpi':get_last_cpi()}

# Calculate the vectors

cpi = implied_inflation_calc(db_uvr_call['cbr'],db_uvr_call['tes_table'],db_uvr_call['last_cpi'])
uvr_projec = calculo_serie_uvr(cpi_serie=cpi['total_cpi'],
                               uvr_db=db_uvr_call['uvr'])
# Assuming uvr_projec is already defined and contains your data

import pandas as pd

# Assuming uvr_projec is already defined and contains your data

# Ensure 'fecha' column is the index and is a datetime type
if 'fecha' in uvr_projec.columns:
    uvr_projec['fecha'] = pd.to_datetime(uvr_projec['fecha'])
    uvr_projec.set_index('fecha', inplace=True)

# Ensure 'valor' column is of numeric type
uvr_projec['valor'] = pd.to_numeric(uvr_projec['valor'], errors='coerce')

# Drop rows with NaN values in 'valor'
uvr_projec.dropna(subset=['valor'], inplace=True)

# Convert index to datetime if it's not already
if not isinstance(uvr_projec.index, pd.DatetimeIndex):
    uvr_projec.index = pd.to_datetime(uvr_projec.index)

# Resample the DataFrame to daily frequency, filling in missing entries with NaN
uvr_projec_daily = uvr_projec.resample('D').asfreq()

# Use linear interpolation to fill in missing values
uvr_projec_interpolated = uvr_projec_daily.interpolate(method='linear')

# Filter out rows with dates less than today
today = pd.Timestamp.today().normalize()  # normalize() to remove the time part
uvr_projec_interpolated = uvr_projec_interpolated[uvr_projec_interpolated.index >= today]

# Drop any rows with null values in the index (date) column
uvr_projec_interpolated = uvr_projec_interpolated.dropna()
uvr_projec_interpolated = uvr_projec_interpolated.reset_index().rename(columns={'index': 'fecha'})
uvr_projec_interpolated['fecha'] = pd.to_datetime(uvr_projec_interpolated['fecha']).apply(str)

# Assuming xty.session is already defined and connected to your database
# Clear existing data if needed (optional)
xty.session.table('uvr_projection').delete().not_.is_('fecha', 'null').execute()

# Insert the cleaned data
xty.session.table('uvr_projection').insert(uvr_projec_interpolated.to_dict(orient='records')).execute()

# uvr_projec.reset_index(inplace=True)
# uvr_projec.rename(columns={'index': 'fecha'}, inplace=True)
# uvr_projec.reset_index(drop=True, inplace=True)
# uvr_projec['fecha'] = uvr_projec['fecha'].astype(str)


cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})

# xty.session.table('inflacion_implicita').insert(cpi['total_cpi'].to_dict(orient='records')).execute()

cpi = cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})
# Convert 'fecha' column to datetime if it's not already
cpi['fecha'] = pd.to_datetime(cpi['fecha'])

# Filter out rows with dates before March 30, 2023
cpi_filtered = cpi[cpi['fecha'] >= pd.Timestamp(2023, 3, 30)]

# Esto borra todos los datos
xty.session.table('inflacion_implicita').delete().not_.is_(
    'fecha', 'null').execute()


# Convert 'fecha' column to string format
cpi_filtered['fecha'] = cpi_filtered['fecha'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Insert the DataFrame into the SQL database
xty.session.table('inflacion_implicita').insert(cpi_filtered.to_dict(orient='records')).execute()

# Creacion de la inflacion implicita en supabase.
#xty.session.table('inflacion_implicita').insert(
 #   cpi.to_dict(orient='records')).execute()

##%

# %%
