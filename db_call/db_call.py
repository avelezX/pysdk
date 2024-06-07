# Este archivo esta disenhado para agrupar todos los llamados a la base de datos. 

from src.xerenity.xty import Xerenity
import os

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)


##########
#Traer la serie de IBR swap overnight, en ea. 

def get_last_banrep(serie_banrep,n=0):
    diccionario_series={
        "Tasa de Desempleo":1,
        "Tasa de Empleo":2,
        "PIB Trimestral - Oferta - Total - Precios Constantes de 2015":3,
        "PIB Trimestral - Oferta - Construcci�n - Precios Constantes de 2015":4,
        "PIB Trimestral - Demanda - Formaci�n bruta de capital - Precios Constantes de 2015":5,
        "PIB Trimestral - Demanda - Consumo Final - Precios Constantes de 2015":6,
        "IPC Base 2018":7,
        "Tasa de Politica Monetaria":8,
        "Indicador Bancario de Referencia (IBR) overnight, nominal":9,
        "Indicador Bancario de Referencia (IBR) overnight, efectiva":10,
        "Indicador Bancario de Referencia (IBR) 1 Mes, nominal":11,
        "Indicador Bancario de Referencia (IBR) 1 Mes, efectiva":12,
        "Indicador Bancario de Referencia (IBR) 3 Meses, nominal":13,
        "Indicador Bancario de Referencia (IBR) 3 Meses, efectiva":14,
        "Indicador Bancario de Referencia (IBR) 6 Meses, nominal":15,
        "Indicador Bancario de Referencia (IBR) 6 Meses, efectiva":16,
        "Indicador Bancario de Referencia (IBR) 12 Meses, nominal":17,
        "Indicador Bancario de Referencia (IBR) 12 Meses, efectiva":18,
        "Unidad de Valor Real (UVR)":19
        }
    serie_br=diccionario_series[serie_banrep]
    if n==0:
        return_s=xty.BanRep().get_econ_data_last(id_serie=serie_br)
    else:
        return_s=xty.BanRep().get_econ_data_last_n(id_serie=serie_br,n=n)
    return return_s

#def get_last_banrep_1():
#    return xty.BanRep().get_econ_data_last(id_serie=1).data[0]['valor']
#get_last_banrep("Tasa de Politica Monetaria",0).data[0]['valor']



#def get_banrep_19():
#    return xty.BanRep().get_econ_data_last(id_serie=19).data[0]['valor']/100

#get_last_banrep("Indicador Bancario de Referencia (IBR) overnight, nominal",0)
#get_last_banrep("Indicador Bancario de Referencia (IBR) overnight, nominal",0).data[0]['valor']/100
#Get last n


######### FALTA EL UVR EN LA NUEVA TABLA DE SUPABASE#####
#def get_last_banrep_8():
#    return xty.BanRep().get_econ_data_last_n(id_serie=8,n=365*2).data
####get_last_banrep(,365*2).data
#get_last_banrep("Unidad de Valor Real (UVR)",n=365*2).data

#def get_banrep_16():
#    return xty.BanRep().get_econ_data_last(id_serie=16).data[0]['valor']/100
#get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal",365*5).data[0]['valor']/100


#def get_last_n_banrep_ibr_1m_nom(n=360*5):
#    return xty.BanRep().get_econ_data_last_n(id_serie=16,n=n).data
#get_last_banrep("Indicador Bancario de Referencia (IBR) 1 Mes, nominal",365*5).data

#def get_last_n_banrep_ibr_3m_nom(n=365*5):
#    return xty.BanRep().get_econ_data_last_n(id_serie=17,n=n).data
#get_last_banrep("Indicador Bancario de Referencia (IBR) 3 Meses, nominal",365*5).data

#def get_last_n_banrep_ibr_6m_nom(n=365*5):
#    return xty.BanRep().get_econ_data_last_n(id_serie=18,n=n).data
#get_last_banrep("Indicador Bancario de Referencia (IBR) 6 Meses, nominal",365*5).data



def get_ibr_cluster_table(initial_date,final_date):
    return xty.get_date_range(table_name='ibr_swaps_cluster',
                              initial_date=initial_date,
                              final_date=final_date,
                              date_column_name='execution_timestamp').data

def get_tes_table():
    return xty.read_table_df('tes')



def get_last_cpi():
    return xty.CPI().lag_last(lag_value=12, canasta_id= 1)

def get_last_cpi_lag():
    return xty.CPI().lag(lag_value=12, canasta_id= 1)



