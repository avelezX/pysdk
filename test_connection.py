import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv

load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
    table_name="banrep_serie"
)

print(xty.get_econ_data_ids().data)
print(xty.BanRep().get_econ_data(id_serie=8).data)

xty.log_out()
