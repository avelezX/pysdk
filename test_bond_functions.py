import os
from src.xerenity.xty import Xerenity
from src.data_source.tes.tes import Tes
from dotenv import load_dotenv
from bond_functions.bond_structure import tes_bond_structure
from bond_functions.bond_curve_structures import BondCurve
import datetime as dt
load_dotenv()

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

# print(xty.read_table('tes_24'))
# print(xty.get_econ_data_ids().data)
# print(xty.BanRep().get_econ_data(id_serie=8).data)
em=dt.date(2019,7,24)
mat=dt.date(2024,7,24)
#bond=tes_bond_structure(emision=em,maturity=mat,cupon=11,name='tes_24',supabase=xty)
#print(bond.db_bond_call())
tes_info=xty.read_table_df('tes')
cop=BondCurve(currency='COP',country='col',bond_info_df=tes_info,supabase=xty)
print(cop.create_df())






