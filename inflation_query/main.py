import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from inflation_query.Inflation_query import implied_inflation_calc
from inflation_query.uvr_calc import calculo_serie_uvr
from inflation_query.plots import total_cpi_mom_image,total_cpi_yoy_image,total_cpi_yoy_plot,total_cpi_mom_plot,uvr_plot,uvr_image
from datetime import datetime

today = datetime(2023, 11, 2)

# Calculate the vectors
cpi=implied_inflation_calc()
uvr_proyec=calculo_serie_uvr(cpi_serie=cpi['total_cpi'])


total_cpi_mom_image(total_cpi_monthly=cpi['total_cpi_monthly'],today=today)
total_cpi_mom_plot(total_cpi_monthly=cpi['total_cpi_monthly'],today=today)
total_cpi_yoy_image(total_cpi_yoy=cpi['total_cpi_yoy'],today=today)
total_cpi_yoy_plot(total_cpi_yoy=cpi['total_cpi_yoy'],today=today)
uvr_plot(uvr_proyec,today=today.date())
uvr_image(uvr_proyec,today=today.date())

