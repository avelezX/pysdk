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

data = xty.get_data()

print(data.head())
print(xty.get_date_columns())

date_range = xty.get_date_range("event_timestamp", final_date="2023-10-25")
print(len(date_range))

xty.log_out()
