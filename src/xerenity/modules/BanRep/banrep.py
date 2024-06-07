from postgrest import APIResponse
from src.xerenity.modules.module_access_constants import MAC

class BanRep_Functions:
    def __init__(self, xerentiy):
        """
        Initializes an instance of BanRep_Functions.

        Args:
        - xerenity: An instance of the Xerenity class.

        Raises:
        - Exception: If the data_name of xerenity is not compatible with BanRep calculations.
        """
        self.xty = xerentiy

        # if self.xty.data_name not in MAC["BanRep"]:
        #     raise Exception(f"{self.xty.data_name} not compatible with BanRep calculations.")

    def get_econ_data(self, id_serie: int) -> APIResponse:
        return self.xty.session.table(table_name="banrep_series_value_v2").select("*").eq(column="id_serie", value=id_serie).order(column="fecha", desc=False).execute()

    def get_econ_data_last(self,id_serie: int) -> APIResponse:
        return self.xty.session.table(table_name="banrep_series_value_v2").select("*").eq(column="id_serie", value=id_serie).order(column="fecha", desc=True).limit(1).execute()
    
    def get_econ_data_last_n(self,id_serie: int,n:int) -> APIResponse:
        return self.xty.session.table(table_name="banrep_series_value_v2").select("*").eq(column="id_serie", value=id_serie).order(column="fecha", desc=True).limit(n).execute()