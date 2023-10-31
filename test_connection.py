import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv

load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD')
)

tes = Tes(xty=xty)

all_src = tes.get_sources()

for src in all_src:
    print('-----------------------------------')
    print(xty.read_table(table_name='tes_24'))

xty.log_out()
