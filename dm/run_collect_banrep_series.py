from data_collectors.banrep_stats.banrep_data_file_collector import BanrepDataCollector
from db_connection.supabase.Client import SupabaseConnection

from data_collectors.banrep_stats.clean_banrep_data_files import yyyyqq_to_datetime, yyyy_mm_to_datetime, \
    yyyymm_to_datetime, yyyy_mm_dd_to_datetime, yyyy_slash_mm_to_datetime, yyyy_mm_dd_H_M_S_to_datetime, get_max_by_date

series = [
    {
        "series_name": "Tasa de Desempleo",
        "id_serie": 1,
        "path": '/shared/Series Estadísticas_T/1. Empleo y desempleo - Serie_empalmada/1.1 Serie histórica/1.1.1.EMP_Total nacional',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Año-Mes (AAAA-MM)": "fecha", "Tasa de desempleo": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_to_datetime]
    }, {
        "series_name": "Tasa de Empleo",
        "id_serie": 2,
        "path": '/shared/Series Estadísticas_T/1. Empleo y desempleo - Serie_empalmada/1.1 Serie histórica/1.1.1.EMP_Total nacional',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Año-Mes (AAAA-MM)": "fecha", "Tasa de empleo": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_to_datetime]
    }, {
        "series_name": "PIB Trimestral - Oferta - Total - Precios Constantes de 2015",
        "id_serie": 3,
        "path": '/shared/Series Estadísticas_T/1. PIB/1. 2015/1.4 PIB_Precios constantes grandes ramas de actividades economicas_trimestral_V2',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Id Trimestre": "fecha", "Valor": "valor"},
        "filter_column_name": "Ramas de actividad económica",
        "filter_column_name_2": None,
        "filter_value": "Producto interno bruto",
        "filter_value_2": None,
        "cleaning_functions": [yyyyqq_to_datetime, get_max_by_date]
    }, {
        "series_name": "PIB Trimestral - Oferta - Construcción - Precios Constantes de 2015",
        "id_serie": 4,
        "path": '/shared/Series Estadísticas_T/1. PIB/1. 2015/1.4 PIB_Precios constantes grandes ramas de actividades economicas_trimestral_V2',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Id Trimestre": "fecha", "Valor": "valor"},
        "filter_column_name": "Ramas de actividad económica",
        "filter_column_name_2": None,
        "filter_value": "Construcción",
        "filter_value_2": None,
        "cleaning_functions": [yyyyqq_to_datetime, get_max_by_date]
    }, {
        "series_name": "PIB Trimestral - Demanda - Formación bruta de capital - Precios Constantes de 2015",
        "id_serie": 5,
        "path": '/shared/Series Estadísticas_T/1. PIB/1. 2015/1.10 PIB_Oferta demanda finales territorio nacional precios constantes_anual_IQY',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Id Trimestre": "fecha", "Valor": "valor"},
        "filter_column_name": "Conceptos PIB",
        "filter_column_name_2": "Descripción en español",
        "filter_value": "Formación bruta de capital",
        "filter_value_2": "Trimestral",
        "cleaning_functions": [yyyyqq_to_datetime, get_max_by_date]
    }, {
        "series_name": "PIB Trimestral - Demanda - Consumo Final - Precios Constantes de 2015",
        "id_serie": 6,
        "path": '/shared/Series Estadísticas_T/1. PIB/1. 2015/1.10 PIB_Oferta demanda finales territorio nacional precios constantes_anual_IQY',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Id Trimestre": "fecha", "Valor": "valor"},
        "filter_column_name": "Conceptos PIB",
        "filter_column_name_2": "Descripción en español",
        "filter_value": "Gasto de consumo final",
        "filter_value_2": "Trimestral",
        "cleaning_functions": [yyyyqq_to_datetime, get_max_by_date]
    }, {
        "series_name": "IPC Base 2018",
        "id_serie": 7,
        "path": '/shared/Series Estadísticas_T/1. IPC base 2018/1.2. Por año/1.2.5.IPC_Serie_variaciones',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Mes Año": "fecha", "Indice": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyymm_to_datetime]
    }, {
        "series_name": "Tasa de Política Monetaria",
        "id_serie": 8,
        "path": '/shared/Series Estadísticas_T/1. Tasa de intervención de política monetaria/1.2.TIP_Serie historica diaria',
        "columns": None,
        "columns_index": None,
        "name_mapping": {"Fecha (dd/mm/aaaa)": "fecha", "Tasa de intervención de política monetaria (%)": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_dd_to_datetime]
    }, {
        # IBR deposit rates (id_serie 9-18) removed — now collected by
        # run_collect_ibr_marks.py (dedicated collector, runs via GitHub Actions).
        "series_name": "Unidad de Valor Real UVR",
        "id_serie": 19,
        "path": '/shared/Series Estadísticas_T/1. UPAC - UVR/1.1 UVR/1.1.2.UVR_Serie historica diaria',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Fecha (dd/mm/aaaa)": "fecha", "Pesos colombianos por UVR": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_dd_to_datetime]
    }, {
        "series_name": "Tasas de interés de los certíficados de depósito a término 90 días (DTF) Mensual",
        "id_serie": 20,
        "path": '/shared/Series Estadísticas_T/1. Tasas de Captación/1.1 Serie empalmada/1.1.3 Mensuales - (Desde enero de 1986)/1.1.3.1.TCA_Para un rango de fechas dado (DTF) IQY',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Fecha": "fecha", "Tasa de interés - efectiva anual %": "valor"},
        "filter_column_name": None,
        "filter_column_name_2": None,
        "filter_value": None,
        "filter_value_2": None,
        "cleaning_functions": [yyyy_slash_mm_to_datetime]
    }, {
        "series_name": "Tasas de interés de los certíficados de depósito a término 90 días (DTF) Semanal E.A.",
        "id_serie": 21,
        "path": '/shared/Series Estadísticas_T/1. Tasas de Captación/1.1 Serie empalmada/1.1.2 Semanales/1.1.2.1 DTF,CDT 180 días,CDT 360 días y TCC - (Desde el 12 de enero de 1984)/1.1.2.1.1.TCA_CSV_XML_Para un rango de fechas dado',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Semana inicio": "fecha", "Tasa de interés - efectiva anual": "valor"},
        "filter_column_name": "Tasa de interés",
        "filter_column_name_2": None,
        "filter_value": "DTF",
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_dd_H_M_S_to_datetime]
    }, {
        "series_name": "Tasas de interés de los certíficados de depósito a término 180 días - Semanal E.A.",
        "id_serie": 22,
        "path": '/shared/Series Estadísticas_T/1. Tasas de Captación/1.1 Serie empalmada/1.1.2 Semanales/1.1.2.1 DTF,CDT 180 días,CDT 360 días y TCC - (Desde el 12 de enero de 1984)/1.1.2.1.1.TCA_CSV_XML_Para un rango de fechas dado',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Semana inicio": "fecha", "Tasa de interés - efectiva anual": "valor"},
        "filter_column_name": "Tasa de interés",
        "filter_column_name_2": None,
        "filter_value": "CDT 180",
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_dd_H_M_S_to_datetime]
    }, {
        "series_name": "Tasas de interés de los certíficados de depósito a término 360 días - Semanal E.A.",
        "id_serie": 23,
        "path": '/shared/Series Estadísticas_T/1. Tasas de Captación/1.1 Serie empalmada/1.1.2 Semanales/1.1.2.1 DTF,CDT 180 días,CDT 360 días y TCC - (Desde el 12 de enero de 1984)/1.1.2.1.1.TCA_CSV_XML_Para un rango de fechas dado',
        "columns": None,
        "column_indexes": None,
        "name_mapping": {"Semana inicio": "fecha", "Tasa de interés - efectiva anual": "valor"},
        "filter_column_name": "Tasa de interés",
        "filter_column_name_2": None,
        "filter_value": "CDT 360",
        "filter_value_2": None,
        "cleaning_functions": [yyyy_mm_dd_H_M_S_to_datetime]
    }
]


connection = SupabaseConnection()
connection.sign_in_as_collector()
banrep = BanrepDataCollector()


for serie in series:

    try:
        print("Pulling file... for " + serie["series_name"])

        df = banrep.get_stock_price(symbol=serie['path'])

        df.rename(columns=serie['name_mapping'], inplace=True)

        if serie['filter_column_name'] != None:
            df = df[df[serie['filter_column_name']] == serie['filter_value']]
            print("Filtered for " + serie["filter_value"])

        else:
            print("No row filtering required")

        if serie['filter_column_name_2'] != None:
            df = df[df[serie['filter_column_name_2']] == serie['filter_value_2']]
            print("Filtered for " + serie["filter_value_2"])

        else:
            print("No second row filtering required")

        df['id_serie'] = serie['id_serie']

        df['valor'] = df['valor'].str.replace(",", ".")
        df['valor'] = df['valor'].astype(float)

        df = df[['id_serie', 'fecha', 'valor']]

        if serie['cleaning_functions'] != None:
            for fn in serie['cleaning_functions']:
                df = fn(df)
            print("All cleaning functions applied")
        else:
            print("No cleaning functions applied")
        
        df['fecha'] = df['fecha'].dt.strftime("%Y-%m-%d")

        last = connection.get_last_by(
            table_name='banrep_series_value_v2',
            column_name='fecha',
            filter_by=('id_serie', serie['id_serie'])
        )

        if len(last) > 0:
            filter_date = last[0]['fecha']
            filtering = df[df['fecha'] > filter_date].copy(deep=True)
        else:
            filtering = df.copy(deep=True)

        connection.insert_dataframe(frame=filtering, table_name='banrep_series_value_v2')
        
    except Exception as e:
        print("Failed to retrieved banrep serie {}".format(str(e)))


