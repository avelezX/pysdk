# Este archivo esta disenhado para agrupar todos los llamados a la base de datos. 

from src.xerenity.xty import Xerenity
import os

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

##########
#Traer la serie de IBR swap overnight, en ea. 
def get_banrep_19():
    return xty.BanRep().get_econ_data_last(id_serie=19).data[0]['valor']/100

def get_banrep_16():
    return xty.BanRep().get_econ_data_last(id_serie=16).data[0]['valor']/100

def get_last_banrep_1():
    return xty.BanRep().get_econ_data_last(id_serie=1).data[0]['valor']

def get_last_banrep_8():
    return xty.BanRep().get_econ_data_last_n(id_serie=8,n=365*2).data

def get_ibr_cluster_table():
    return xty.get_date_range(table_name='ibr_swaps_cluster',date_column_name='execution_timestamp').data

def get_tes_table():
    return xty.read_table_df('tes')



def get_last_cpi():
    return xty.CPI().lag_last(lag_value=12, canasta_id= 1)

def get_last_cpi_lag():
    return xty.CPI().lag(lag_value=12, canasta_id= 1)


def get_last_n_banrep_ibr_1m_nom(n=360*5):
    return xty.BanRep().get_econ_data_last_n(id_serie=16,n=n).data

def get_last_n_banrep_ibr_3m_nom(n=365*5):
    return xty.BanRep().get_econ_data_last_n(id_serie=17,n=n).data

def get_last_n_banrep_ibr_6m_nom(n=365*5):
    return xty.BanRep().get_econ_data_last_n(id_serie=18,n=n).data
