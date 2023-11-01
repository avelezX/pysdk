import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv

load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
    table_name="ibr_swaps"
)

print(len(xty.get_date_range().data))

xty.log_out()
