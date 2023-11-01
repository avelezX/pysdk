import os
from supabase import Client
from supabase import create_client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()


class Xerenity:

    def __init__(self, username: str, password: str, table_name: str, auto_refresh: bool = False):
        # Attribute Initialization
        url: str = os.getenv('XTY_URL')
        key: str = os.getenv('XTY_TOKEN')
        opts = ClientOptions(auto_refresh_token=auto_refresh).replace(schema="xerenity")
        self.data: pd.DataFrame = pd.DataFrame()
        self.data_name: str = table_name

        # Connection Client Initialization
        self.session: Client = create_client(url, key, options=opts)

        self.session.auth.sign_in_with_password(
            {
                "email": username,
                "password": password
            }
        )

        # Table Extraction
        raw_data = self.read_table(table_name).data
        self.data = self.convert_df(raw_data)

    # ---------------------------------------
    # Basic Functions
    # --------------------------------------

    def log_out(self) -> None:
        """

        Logs out user from current session
        https://supabase.com/docs/reference/python/auth-signout
        :return: None
        """

        self.session.auth.sign_out()

    def get_data(self):
        """Returns the data retrieved from DB

        Returns:
            The retrieved data from DB
        """
        return self.data

    def get_data_name(self):
        """Returns the data name retrieved from DB

        Returns:
            The retrieved data name from DB
        """
        return self.data_name

    def read_table(self, table_name):
        """

        Retrieves all data from a given source
        :param table_name: table source to be read from
        :return:
        """
        return self.session.table(table_name=table_name).select('*').execute()

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

    def get_date_columns(self) -> list:
        """
        Returns a list of column names with datetime64[ns] data type in the DataFrame.

        Returns:
        - List[str]: List of column names with datetime data type.
        """
        df = self.data
        return [column for column in df.columns if df[column].dtype == 'datetime64[ns]']

    # --------------------------------------
    # DF Advanced Manipulation Functions
    # --------------------------------------

    def get_date_range(self, date_column_name: str = None, initial_date: np.datetime64 = None,
                       final_date: np.datetime64 = None):
        """
        Filters data based on date column and specified date range.

        Args:
        - date_column_name (Optional[str]): Name of the date column.
        - initial_date (Optional[np.datetime64]): Initial date for filtering.
        - final_date (Optional[np.datetime64]): Final date for filtering.

        Returns:
        - pd.DataFrame: Filtered DataFrame based on the specified date range.
        """
        date_cols = self.get_date_columns()
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
            return self.data[
                (self.data[filter_by] >= initial_date) & (self.data[filter_by] <= final_date)]
        elif initial_date:
            return self.data[self.data[filter_by] >= initial_date]
        elif final_date:
            return self.data[self.data[filter_by] <= final_date]
        else:
            return self.data
