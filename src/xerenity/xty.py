import os
import sys
#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
sys.path.append("/Users/andre/Documents/xerenity/pysdk")
from supabase import Client
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from src.xerenity.modules.BanRep.banrep import BanRep_Functions
from src.xerenity.modules.CPI.cpi import CPI_Functions
from dotenv import load_dotenv
import pandas as pd
from postgrest import APIResponse
from src.xerenity.modules.module_access_constants import MAC

load_dotenv()

class Xerenity:

    def __init__(self, username: str, password: str, auto_refresh: bool = False):
        # Attribute Initialization
        url: str = os.getenv('XTY_URL')
        key: str = os.getenv('XTY_TOKEN')
        opts = ClientOptions(auto_refresh_token=auto_refresh).replace(schema="xerenity")
        #self.data_name: str = table_name

        # Connection Client Initialization
        self.session: Client = create_client(url, key, options=opts)
        collector_bearer= os.getenv('XTY_COLLECTOR')
        self.session.postgrest.session.headers["Authorization"] = "Bearer " + collector_bearer
        print(collector_bearer)
        print("----COllector bearer----")
        
        """
        print(username)
        print("------USER----")
        
        self.session.auth.sign_in_with_password(
            {
                "email": username,
                "password": password
            }
        )
        """
    # ---------------------------------------
    # Subclases for Modules
    # --------------------------------------

    def CPI(self) -> CPI_Functions:
        """
        Creates an instance of the CPI_Functions class, allowing access to CPI-related functions.

        Returns:
        - CPI_Functions: An instance of the CPI_Functions class.
        """
        return CPI_Functions(self)

    def get_cpi_tables(self) -> list:
        """
        Retrieves the CPI tables from the MAC dictionary.

        Returns:
        - list: A list containing the CPI-related tables from the MAC dictionary.
        """
        return MAC["CPI"]

    def BanRep(self) -> BanRep_Functions:
        return BanRep_Functions(self)

    def get_banrep_tables(self) -> list:
        return MAC["BanRep"]

    def get_econ_data_ids(self):
        return self.session.table(table_name="banrep_serie_v2").select("id, nombre").execute()

    # --------------------------------------
    # Basic Functions
    # --------------------------------------

    def log_out(self) -> None:
        """

        Logs out user from current session
        https://supabase.com/docs/reference/python/auth-signout
        :return: None
        """

        self.session.auth.sign_out()

    def get_data_name(self):
        """Returns the data name retrieved from DB

        Returns:
            The retrieved data name from DB
        """
        return self.data_name

    def read_table(self,table_name) -> APIResponse:
        """

        Retrieves all data from a given source
        :param table_name: table source to be read from
        :return:
        """
        return self.session.table(table_name=table_name).select('*').execute().data
    
    def read_table_df(self,table_name) -> pd.DataFrame:
        return pd.DataFrame(self.read_table(table_name))
    

    def convert_df(self, data: list) -> pd.DataFrame:
        """
        Converts a list of data into a DataFrame, infers and converts date columns to datetime format.

        Args:
        - data (List): List of data to be converted into a DataFrame.

        Returns:
        - pd.DataFrame: DataFrame with inferred datetime columns.
        """
        df = pd.DataFrame(data)
        df = self.infer_date_types(df)

        return df

    # --------------------------------------
    # DF Basic Manipulation Functions
    # --------------------------------------

    def infer_date_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Infers and converts columns in a DataFrame to datetime format.

        Args:
        - df (pd.DataFrame): The input DataFrame.

        Returns:
        - pd.DataFrame: DataFrame with inferred datetime columns.
        """
        for column in df.columns:
            if df[column].dtype == 'O' and df[column].notna().any():
                # Check if it's an object not null (assuming date columns are in string format)
                try:
                    df[column] = pd.to_datetime(df[column])
                except ValueError:
                    pass  # Ignore if not convertible

        return df

    def get_date_columns(self,table_name: str = None ) -> list:
        """
        Returns a list of column names with datetime64[ns] data type in the DataFrame.

        Returns:
        - List[str]: List of column names with datetime data type.
        """
        df = self.convert_df(self.read_table(table_name=table_name))
        return [column for column in df.columns if df[column].dtype == 'datetime64[ns]']

    # --------------------------------------
    # DF Advanced Manipulation Functions
    # --------------------------------------

    def get_date_range(self,table_name: str = None ,date_column_name: str = None, initial_date: str = None,
                       final_date: str = None) -> APIResponse:
        """
        Filters data based on date column and specified date range.

        Args:
        - date_column_name (Optional[str]): Name of the date column.
        - initial_date (Optional[str]): Initial date for filtering.
        - final_date (Optional[str]): Final date for filtering.

        Returns:
        - APIResponse: Filtered DataFrame based on the specified date range.
        """
        base_table = self.session.table(table_name=table_name).select('*')
        date_cols = self.get_date_columns(table_name=table_name)
        filter_by = date_column_name

        if len(date_cols) == 0:
            raise Exception("There's no columns to perform date range filtering.")

        if filter_by and date_column_name not in date_cols:
            raise Exception(f"Specified date column {date_column_name} not in {self.data_name}.")

        if not filter_by and len(date_cols) > 1:
            raise Exception(
                f"Please specify the column to perform date range filtering. Available columns: {date_cols}")

        if not filter_by and len(date_cols) == 1:
            filter_by = date_cols[0]

        # Perform date range filtering
        if initial_date and final_date:
            return base_table.gte(column=filter_by, value=initial_date).lte(column=filter_by, value=final_date).order(column=filter_by, desc=True).execute()
        elif initial_date:
            return base_table.gte(column=filter_by, value=initial_date).execute()
        elif final_date:
            return base_table.lte(column=filter_by, value=final_date).execute()
        else:
            return base_table.execute()


