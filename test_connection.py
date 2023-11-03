import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv
import pandas as pd
import datetime as dt
load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

#print(xty.read_table('tes_24'))

#print(pd.DataFrame(xty.CPI().lag(lag_value=12, canasta_id= 1).data))
response=xty.CPI().lag(lag_value=12, canasta_id= 1)
response['fecha'] = pd.to_datetime(response.index.map(lambda x: f"{x.year}-{x.month}-15"))
response.set_index('fecha', inplace=True)
#response=pd.read_json(response['cpi_index'])
#print(pd.DataFrame(response['cpi_index']))
print(response)
xty.log_out()
