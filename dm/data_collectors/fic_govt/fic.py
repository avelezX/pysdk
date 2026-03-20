import sys
sys.path.append('C:/GitHub/xerenity-dm')

import requests
import pandas as pd
from data_collectors.dtcc.dtcc_collector import DttcColelctor
from datetime import datetime, timedelta


class ficCollector(DttcColelctor):
    def __init__(self):
        super().__init__(name='fic')

        self.has_intra_day_prices = False
        self.periodicity = 'd'

        self.url = 'https://www.datos.gov.co/resource/qhpu-8ixx.json?fecha_corte='

        # All 26 API columns from datos.gov.co
        self.columns = [
            'fecha_corte', 'tipo_entidad', 'nombre_tipo_entidad', 'codigo_entidad', 'nombre_entidad',
            'tipo_negocio', 'nombre_tipo_patrimonio', 'subtipo_negocio', 'nombre_subtipo_patrimonio',
            'codigo_negocio', 'nombre_patrimonio', 'principal_compartimento', 'tipo_participacion',
            'rendimientos_abonados', 'precierre_fondo_dia_t', 'numero_unidades_fondo_cierre',
            'valor_unidad_operaciones', 'aportes_recibidos', 'retiros_redenciones', 'anulaciones',
            'valor_fondo_cierre_dia_t', 'numero_inversionistas',
            'rentabilidad_diaria', 'rentabilidad_mensual', 'rentabilidad_semestral', 'rentabilidad_anual'
        ]

        # Numeric columns that need explicit casting (API returns strings)
        self.numeric_columns = [
            'tipo_entidad', 'codigo_entidad', 'tipo_negocio', 'subtipo_negocio',
            'codigo_negocio', 'principal_compartimento', 'tipo_participacion',
            'rendimientos_abonados', 'precierre_fondo_dia_t', 'numero_unidades_fondo_cierre',
            'valor_unidad_operaciones', 'aportes_recibidos', 'retiros_redenciones',
            'anulaciones', 'valor_fondo_cierre_dia_t', 'numero_inversionistas',
            'rentabilidad_diaria', 'rentabilidad_mensual', 'rentabilidad_semestral',
            'rentabilidad_anual'
        ]

    def get_raw_data(self, date):
        formatted_date = date.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
        url = f'{self.url}{formatted_date}T00:00:00.000'
        return requests.get(url)

    def clean_raw_data(self, row_data_json):

        if row_data_json.status_code == 200:
            df = pd.DataFrame(row_data_json.json())

            if df.empty:
                return df

            # Clean wrong special characters in: nombre_patrimonio
            patt = ['INVERSI�N', 'D�LARES', 'INNOVACI�N', 'LIQUIDACI�N', 'AM�RICA',
                    'FIDUPA�S', 'AÑ�S', 'INTER�S', 'NACI�N', 'M�NIMA',
                    'M�S', 'GESTI�N', 'T�TULOS', 'SECCI�N', 'BOGOT�',
                    'ITA�', 'MULTIACCI�N', 'BURS�TIL', 'CR�DITO', 'DIN�MICO',
                    'PA�S ', 'SINT�TICO', 'LOG�STIC', 'DIVERSIFICACI�N',
                    '�PTIMO', 'REDUCCI�N', 'PROGRESI�N', 'RENTAPL�S', 'P�RAMO',
                    'FINANCIACI�N', 'CONSTRUCCI�N', '90�', 'PARTICIPACI�N', 'P�BLICA', 'FIDUACCI�N',
                    'D�AS', 'ENERG�A', 'REDENCI�N', 'ULTRACCI�N', 'OPCI�N']

            repl = ['INVERSIÓN', 'DÓLARES', 'INNOVACIÓN', 'LIQUIDACIÓN', 'AMÉRICA',
                    'FIDUPAÍS', 'AÑOS', 'INTERÉS', 'NACIÓN', 'MÍNIMA',
                    'MÁS', 'GESTIÓN', 'TÍTULOS', 'SECCIÓN', 'BOGOTÁ',
                    'ITAÚ', 'MULTIACCIÓN', 'BURSÁTIL', 'CRÉDITO', 'DINÁMICO',
                    'PAÍS ', 'SINTÉTICO', 'LOGÍSTIC', 'DIVERSIFICACIÓN',
                    'ÓPTIMO', 'REDUCCIÓN', 'PROGRESIÓN', 'RENTAPLÚS', 'PÁRAMO',
                    'FINANCIACIÓN', 'CONSTRUCCIÓN', '90º', 'PARTICIPACIÓN', 'PÚBLICA', 'FIDUACCIÓN',
                    'DÍAS', 'ENERGÍA', 'REDENCIÓN', 'ULTRACCIÓN', 'OPCIÓN']

            for i, j in zip(patt, repl):
                df['nombre_patrimonio'] = df['nombre_patrimonio'].str.replace(i, j)

            # Clean wrong special characters in: nombre_entidad
            patt = ['Ita�', 'Acci�n', 'Bogot�', 'Pa�s', 'Compa�ia',
                    'Compa��a', 'Compañ�a']

            repl = ['Itaú', 'Acción', 'Bogotá', 'País', 'Compañia',
                    'Compañía', 'Compañía']

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
            for col in self.columns:
                if col not in df.columns:
                    df[col] = None

            df = df[self.columns]

            # Cast numeric columns
            for col in self.numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Computed columns
            df['key_id'] = (df['fecha_corte'].astype(str).str[:10] + '_' +
                            df['codigo_negocio'].astype(str).str.replace('.0', '', regex=False) + '_' +
                            df['tipo_participacion'].astype(str).str.replace('.0', '', regex=False))
            df['series_id'] = (df['codigo_negocio'].astype(str).str.replace('.0', '', regex=False) + '_' +
                               df['tipo_participacion'].astype(str).str.replace('.0', '', regex=False))

            return df
        else:
            print(row_data_json.status_code)