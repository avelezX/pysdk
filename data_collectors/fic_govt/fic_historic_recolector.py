import pandas as pd
import requests
import QuantLib as ql
from db_connection.supabase.Client import SupabaseConnection

from functions_DM.colombia_calendar import calendar_colombia


# Set up the Colombian calendar
col_calendar = calendar_colombia()

# All 26 API columns from datos.gov.co
selected_columns = [
    'fecha_corte', 'tipo_entidad', 'nombre_tipo_entidad', 'codigo_entidad', 'nombre_entidad',
    'tipo_negocio', 'nombre_tipo_patrimonio', 'subtipo_negocio', 'nombre_subtipo_patrimonio',
    'codigo_negocio', 'nombre_patrimonio', 'principal_compartimento', 'tipo_participacion',
    'rendimientos_abonados', 'precierre_fondo_dia_t', 'numero_unidades_fondo_cierre',
    'valor_unidad_operaciones', 'aportes_recibidos', 'retiros_redenciones', 'anulaciones',
    'valor_fondo_cierre_dia_t', 'numero_inversionistas',
    'rentabilidad_diaria', 'rentabilidad_mensual', 'rentabilidad_semestral', 'rentabilidad_anual'
]

# Numeric columns that need explicit casting
numeric_columns = [
    'tipo_entidad', 'codigo_entidad', 'tipo_negocio', 'subtipo_negocio',
    'codigo_negocio', 'principal_compartimento', 'tipo_participacion',
    'rendimientos_abonados', 'precierre_fondo_dia_t', 'numero_unidades_fondo_cierre',
    'valor_unidad_operaciones', 'aportes_recibidos', 'retiros_redenciones',
    'anulaciones', 'valor_fondo_cierre_dia_t', 'numero_inversionistas',
    'rentabilidad_diaria', 'rentabilidad_mensual', 'rentabilidad_semestral',
    'rentabilidad_anual'
]

# Start date
start_date = ql.Date(1, 1, 2010)

# End date (today)
end_date = ql.Date.todaysDate()



def fic_historical_colector(start_date=None, end_date=None):
    # Base URL
    base_url = 'https://www.datos.gov.co/resource/qhpu-8ixx.json?$limit=1000000&fecha_corte='

    distinct_date = requests.get(
        "https://www.datos.gov.co/resource/qhpu-8ixx.json?$query=select distinct fecha_corte limit 150000"
    )

    distinct_date_df = pd.DataFrame(distinct_date.json())

    print(distinct_date.json())
    distinct_date_df = pd.DataFrame(distinct_date_df)

    for date in distinct_date_df['fecha_corte']:

        url = base_url + date

        # Request data
        day_tester = requests.get(url)

        print(day_tester.status_code)
        if day_tester.status_code == 200:
            df = pd.DataFrame(day_tester.json())

            if df.empty:
                continue

            # Clean wrong special characters in: nombre_patrimonio
            patt = ['INVERSI\ufffdN', 'D\ufffdLARES', 'INNOVACI\ufffdN', 'LIQUIDACI\ufffdN', 'AM\ufffdRICA',
                    'FIDUPA\ufffdS', 'A\u00d1\ufffdS', 'INTER\ufffdS', 'NACI\ufffdN', 'M\ufffdNIMA',
                    'M\ufffdS', 'GESTI\ufffdN', 'T\ufffdTULOS', 'SECCI\ufffdN', 'BOGOT\ufffd',
                    'ITA\ufffd', 'MULTIACCI\ufffdN', 'BURS\ufffdTIL', 'CR\ufffdDITO', 'DIN\ufffdMICO',
                    'PA\ufffdS ', 'SINT\ufffdTICO', 'LOG\ufffdSTIC', 'DIVERSIFICACI\ufffdN',
                    '\ufffdPTIMO', 'REDUCCI\ufffdN', 'PROGRESI\ufffdN', 'RENTAPL\ufffdS', 'P\ufffdRAMO',
                    'FINANCIACI\ufffdN', 'CONSTRUCCI\ufffdN', '90\ufffd', 'PARTICIPACI\ufffdN', 'P\ufffdBLICA', 'FIDUACCI\ufffdN',
                    'D\ufffdAS', 'ENERG\ufffdA', 'REDENCI\ufffdN', 'ULTRACCI\ufffdN', 'OPCI\ufffdN']

            repl = ['INVERSI\u00d3N', 'D\u00d3LARES', 'INNOVACI\u00d3N', 'LIQUIDACI\u00d3N', 'AM\u00c9RICA',
                    'FIDUPA\u00cdS', 'A\u00d1OS', 'INTER\u00c9S', 'NACI\u00d3N', 'M\u00cdNIMA',
                    'M\u00c1S', 'GESTI\u00d3N', 'T\u00cdTULOS', 'SECCI\u00d3N', 'BOGOT\u00c1',
                    'ITA\u00da', 'MULTIACCI\u00d3N', 'BURS\u00c1TIL', 'CR\u00c9DITO', 'DIN\u00c1MICO',
                    'PA\u00cdS ', 'SINT\u00c9TICO', 'LOG\u00cdSTIC', 'DIVERSIFICACI\u00d3N',
                    '\u00d3PTIMO', 'REDUCCI\u00d3N', 'PROGRESI\u00d3N', 'RENTAPL\u00daS', 'P\u00c1RAMO',
                    'FINANCIACI\u00d3N', 'CONSTRUCCI\u00d3N', '90\u00ba', 'PARTICIPACI\u00d3N', 'P\u00daBLICA', 'FIDUACCI\u00d3N',
                    'D\u00cdAS', 'ENERG\u00cdA', 'REDENCI\u00d3N', 'ULTRACCI\u00d3N', 'OPCI\u00d3N']

            for i, j in zip(patt, repl):
                df['nombre_patrimonio'] = df['nombre_patrimonio'].str.replace(i, j)

            # Clean wrong special characters in: nombre_entidad
            patt = ['Ita\ufffd', 'Acci\ufffdn', 'Bogot\ufffd', 'Pa\ufffds', 'Compa\ufffdia',
                    'Compa\ufffd\ufffda', 'Compa\u00f1\ufffda']

            repl = ['Ita\u00fa', 'Acci\u00f3n', 'Bogot\u00e1', 'Pa\u00eds', 'Compa\u00f1ia',
                    'Compa\u00f1\u00eda', 'Compa\u00f1\u00eda']

            for i, j in zip(patt, repl):
                df['nombre_entidad'] = df['nombre_entidad'].str.replace(i, j)

            # Title case for text columns
            df['nombre_patrimonio'] = df['nombre_patrimonio'].str.title()
            df['nombre_subtipo_patrimonio'] = df['nombre_subtipo_patrimonio'].str.title()

            df['nombre_patrimonio'] = df['nombre_patrimonio'].str.replace('Fic', 'FIC')
            df['nombre_subtipo_patrimonio'] = df['nombre_subtipo_patrimonio'].str.replace('Fic', 'FIC')

            if 'nombre_tipo_patrimonio' in df.columns:
                df['nombre_tipo_patrimonio'] = df['nombre_tipo_patrimonio'].str.title()
                df['nombre_tipo_patrimonio'] = df['nombre_tipo_patrimonio'].str.replace('Fic', 'FIC')

            # Keep only expected columns (fill missing ones with None)
            for col in selected_columns:
                if col not in df.columns:
                    df[col] = None

            full_dataframe = df[selected_columns]

            # Cast numeric columns
            for col in numeric_columns:
                if col in full_dataframe.columns:
                    full_dataframe[col] = pd.to_numeric(full_dataframe[col], errors='coerce')

            # Computed columns
            full_dataframe['key_id'] = (full_dataframe['fecha_corte'].astype(str).str[:10] + '_' +
                                        full_dataframe['codigo_negocio'].astype(str).str.replace('.0', '', regex=False) + '_' +
                                        full_dataframe['tipo_participacion'].astype(str).str.replace('.0', '', regex=False))
            full_dataframe['series_id'] = (full_dataframe['codigo_negocio'].astype(str).str.replace('.0', '', regex=False) + '_' +
                                           full_dataframe['tipo_participacion'].astype(str).str.replace('.0', '', regex=False))

            yield full_dataframe
