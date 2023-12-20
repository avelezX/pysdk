import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from inflation_query.Inflation_query import implied_inflation_calc
from inflation_query.uvr_calc import calculo_serie_uvr
from inflation_query.plots import total_cpi_mom_image,total_cpi_yoy_image,total_cpi_yoy_plot,total_cpi_mom_plot,uvr_plot,uvr_image
from datetime import datetime
from src.xerenity.xty import Xerenity
import os
import pandas as pd
today = datetime(2023, 11, 2)

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

# Calculate the vectors
cpi=implied_inflation_calc()
uvr_projec=calculo_serie_uvr(cpi_serie=cpi['total_cpi'])

uvr_projec.reset_index(inplace=True)
uvr_projec.rename(columns={'index': 'fecha'}, inplace=True)
uvr_projec.reset_index(drop=True, inplace=True)
uvr_projec['fecha'] = uvr_projec['fecha'].astype(str)
xty.session.table('uvr_projection').delete().not_.is_('fecha', 'null').execute()
xty.session.table('uvr_projection').insert(uvr_projec.to_dict(orient='records')).execute()

# uvr_proyec.to_clipboard()
# cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})

# xty.session.table('inflacion_implicita').insert(cpi['total_cpi'].to_dict(orient='records')).execute()

cpi = cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})
cpi['fecha'] = pd.to_datetime(cpi['fecha']).apply(str)
print(cpi.to_dict(orient='records'))

#Esto borra todos los datos
xty.session.table('inflacion_implicita').delete().not_.is_('fecha', 'null').execute()
#Creacion de la inflacion implicita en supabase. 
xty.session.table('inflacion_implicita').insert(cpi.to_dict(orient='records')).execute()
### Creacion de series de tiempo y figuras para entrega temporal. 

#total_cpi_mom_image(total_cpi_monthly=cpi['total_cpi_monthly'],today=today)
#total_cpi_mom_plot(total_cpi_monthly=cpi['total_cpi_monthly'],today=today)
#total_cpi_yoy_image(total_cpi_yoy=cpi['total_cpi_yoy'],today=today)
#total_cpi_yoy_plot(total_cpi_yoy=cpi['total_cpi_yoy'],today=today)
#uvr_plot(uvr_proyec,today=today.date())
#uvr_image(uvr_proyec,today=today.date())



