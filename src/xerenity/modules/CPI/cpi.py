from postgrest import APIResponse
import pandas as pd
from src.xerenity.modules.module_access_constants import MAC


class CPI_Functions:
    def __init__(self, xerenity):
        """
        Initializes an instance of CPI_Functions.

        Args:
        - xerenity: An instance of the Xerenity class.

        Raises:
        - Exception: If the data_name of xerenity is not compatible with CPI calculations.
        """
        self.xty = xerenity

        # if self.xty.data_name not in MAC["CPI"]:
        #     raise Exception(f"{self.xty.data_name} not compatible with CPI calculations.")

    def lag(self, lag_value: int, canasta_id: int = 1) -> APIResponse:
        """
        Performs CPI index change calculation with a lag.

        Args:
        - lag_value (int): The lag value for the calculation.
        - canasta_id (int): The ID of the canasta for the calculation. Defaults to 1.

        Returns:
        - dict: The result of the CPI index change calculation.
        """
        response= self.xty.session.rpc(
            'cpi_index_change',
            {
                'lag_value': lag_value,
                'id_canasta_search': canasta_id
            }
        ).execute().data
        return pd.DataFrame(response['cpi_index'])
    
    def lag_last(self, lag_value: int, canasta_id: int = 1) -> APIResponse:
        """
        Performs CPI index change calculation with a lag.

        Args:
        - lag_value (int): The lag value for the calculation.
        - canasta_id (int): The ID of the canasta for the calculation. Defaults to 1.

        Returns:
        - value: The result of the CPI index change calculation last value
        """
        df_inflation= self.xty.session.rpc(
            'cpi_index_change',
            {
                'lag_value': lag_value,
                'id_canasta_search': canasta_id
            }
        ).execute()
        df = pd.DataFrame(df_inflation.data)
        df['percentage_change'] = df['cpi_index'].apply(lambda x: x.get('percentage_change'))
        df = df.sort_index()

        return df['percentage_change'].iloc[-1] 
    
