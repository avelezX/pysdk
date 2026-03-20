import requests
import pandas as pd
import datetime
from data_collectors.DataCollector import DataCollector
from datetime import datetime


class DaneCollector(DataCollector):
    def __init__(self):
        super().__init__(name='dtcc_ibr')
        self.has_intra_day_prices = True
        self.base_url = "https://sen.dane.gov.co/services_ipc/rest/IpcServices/getContAndVarFoodBByDateVarAndRegion/"
        self.total_index_url = "https://sen.dane.gov.co/services_ipc/rest/IpcServices/getTendTotVarIndByDateAndPeriod/"

        # https://sen.dane.gov.co/services_ipc/rest/IpcServices/getTendTotVarIndByDateAndPeriod/2023/09/Mensual

    def get_raw_data(self, month, year):
        try:
            url = f"{self.base_url}{year}/{month:02d}/Mensual/Nacional"
            response = requests.get(url)
            response.raise_for_status()  # This will raise an HTTPError for bad responses.

            data_list = response.json()
            return data_list  # Return the list of dictionaries

        except requests.exceptions.HTTPError as errh:
            print(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            print(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            print(f"Oops, something went wrong: {err}")

    def get_cleaned_raw_data(self, month, year):
        raw_data = self.get_raw_data(month=month, year=year)

        clean_data = []
        remove_keys = ['canasta', 'concepto']
        replace_keys = {'value': 'valor'}
        for data_point in raw_data:
            new_val = {}
            for key, value in data_point.items():
                key = str(key).lower()
                if key in remove_keys:
                    continue
                if key in replace_keys:
                    key = replace_keys[key]

                if key == 'id_canasta':
                    new_val[key] = int(value)
                else:
                    try:
                        new_val[key] = str(datetime.strptime(value, "%Y%m%d"))
                    except Exception as e:
                        try:
                            new_val[key] = float(value)
                        except Exception as e:
                            new_val[key] = value

            clean_data.append(new_val)

        return clean_data

    def get_raw_data_index(self, month=datetime.now().month, year=datetime.now().year):
        try:
            url = f"{self.total_index_url}{year}/{month:02d}/Mensual"
            response = requests.get(url)
            response.raise_for_status()  # This will raise an HTTPError for bad responses.

            data_list = response.json()
            return [{key.replace('FECHA', 'Fecha'): value for key, value in entry.items()} for entry in
                    data_list]  # Return the list of dictionaries

        except requests.exceptions.HTTPError as errh:
            print(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            print(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            print(f"Oops, something went wrong: {err}")

    def create_dataframe_indice(self, data_list, column_name='Id_Canasta'):
        df = pd.DataFrame(data_list)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y%m%d')
        df_indice = df.pivot_table(index='Fecha', columns=column_name, values='indice', aggfunc='first')
        df_indice = df_indice.set_index('Fecha')
        return df_indice.applymap(pd.to_numeric)

    def create_dataframe_contribucion(self, data_list, column_name='Id_Canasta'):
        df = pd.DataFrame(data_list)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y%m%d')
        df_contribucion = df.pivot_table(index='Fecha', columns=column_name, values='ValorContribucion',
                                         aggfunc='first')
        test_1 = df_contribucion.reset_index()
        test_1.columns.name = None
        test_1 = test_1.set_index('Fecha')
        return test_1.map(pd.to_numeric)

    def created_df_with_names_idcansta(self, month=9, year=2023):
        return pd.DataFrame(self.get_raw_data(month, year))[['Id_Canasta', 'Canasta']]

    def create_dataframe_index(self, data_list, month, year):
        df = pd.DataFrame(data_list)
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df = df.loc[(df['Fecha'].dt.month == month) & (df['Fecha'].dt.year == year)]
        df = df.rename(columns={'PROMEDIO': 'Total'})
        df = df[['Fecha', 'Total']].set_index('Fecha')
        return df.map(pd.to_numeric)

    def joint_both_index_group(self, month, year, col_names="Code"):
        df_g = self.create_dataframe_contribucion(self.get_raw_data(month, year))
        df_i = self.create_dataframe_index(self.get_raw_data_index(month, year), month, year)
        df = pd.concat([df_g, df_i], axis=1)

        if col_names != "Code":
            df_names = self.create_canasta_table(self.get_raw_data(9, 2023))
            map_dir = dict(zip(df_names['Id_Canasta'], df_names['Canasta']))

            map_dir['Total'] = 'Total'

            df.columns = df.columns.map(map_dir)
        return df

    def create_canasta_table(self, data_list):
        canasta_df = pd.DataFrame(data_list, columns=['Id_Canasta', 'Canasta']).drop_duplicates()
        return canasta_df

    def generate_monthly_data(self, start_month, start_year, end_month, end_year, col_names="Code"):
        dfs = self.joint_both_index_group(start_month, start_year, col_names)
        current_year = start_year
        current_month = start_month

        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            df = self.joint_both_index_group(current_month, current_year, col_names)
            dfs = pd.concat([dfs, df])

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return dfs
