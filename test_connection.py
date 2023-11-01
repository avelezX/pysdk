import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv

load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
    table_name="canasta_values"
)

print(xty.CPI().lag(lag_value=12, canasta_id=1).data)

xty.log_out()
