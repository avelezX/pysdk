import pandas as pd
import requests
import urllib.parse


SUPABASE_URL = "https://tvpehjbqxpiswkqszwwv.supabase.co"
SUPABASE_KEY = "sb_publishable_j8Qlvv34vDqMAC01fQE8GA_-DmBfreq"
COLLECTOR_BEARER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiAiY29sbGVjdG9yIiwiZXhwIjogMTg0NzI4ODUyMCwiaWF0IjogMTczNjk1NTc1MiwiaXNzIjogImh0dHBzOi8vdHZwZWhqYnF4cGlzd2txc3p3d3Yuc3VwYWJhc2UuY28iLCJlbWFpbCI6ICJzdmVsZXpzYWZmb25AZ21haWwuY29tIiwicm9sZSI6ICJjb2xsZWN0b3IifQ.5HX_n8SsXN4xPslndvyyYubdlDLFg2_uAUIwinEi-eU"
SCHEMA = "xerenity"


class SupabaseConnection:
    """
    Supabase REST client using requests directly.
    Replaces supabase-py 1.x which does not support the new publishable key format.
    Same public interface as before so all collectors work unchanged.
    """

    def __init__(self, auto_refresh: bool = False):
        self.collector_bearer = COLLECTOR_BEARER
        self._url = SUPABASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Accept-Profile": SCHEMA,
            "Content-Profile": SCHEMA,
        })

    def sign_in_as_collector(self):
        """Switch Authorization to collector JWT for write access."""
        self.session.headers["Authorization"] = f"Bearer {self.collector_bearer}"

    def sign_is_as_user(self, user_name, password):
        print(f"Login as {user_name} not supported in requests-based client")

    def close(self):
        self.session.close()

    # ── Internal helpers ──

    def _get(self, table: str, params: str = "") -> list:
        r = self.session.get(f"{self._url}/rest/v1/{table}?{params}")
        r.raise_for_status()
        return r.json()

    def _post(self, table: str, rows: list):
        r = self.session.post(
            f"{self._url}/rest/v1/{table}",
            json=rows,
            headers={"Prefer": "return=minimal"},
        )
        if r.status_code not in (200, 201):
            if r.status_code == 409 or "duplicate" in r.text.lower():
                pass  # silently skip duplicates
            else:
                print(f"Insert error {r.status_code}: {r.text[:200]}")

    def _patch(self, table: str, eq_col: str, eq_val, data: dict):
        r = self.session.patch(
            f"{self._url}/rest/v1/{table}?{eq_col}=eq.{urllib.parse.quote(str(eq_val))}",
            json=data,
        )
        if r.status_code not in (200, 204):
            print(f"Update error {r.status_code}: {r.text[:200]}")

    def _delete(self, table: str, params: str):
        r = self.session.delete(f"{self._url}/rest/v1/{table}?{params}")
        r.raise_for_status()
        return r.json()

    # ── Public interface (same as before) ──

    def get_last_by(self, table_name: str, column_name: str, filter_by=None) -> list:
        params = f"select=*&order={column_name}.desc&limit=1"
        if filter_by:
            col, val = filter_by
            params += f"&{col}=eq.{urllib.parse.quote(str(val))}"
        return self._get(table_name, params)

    def read_table(self, table_name: str) -> list:
        return self._get(table_name, "select=*")

    def read_table_limit(self, table_name: str, limit: int, filter_by=None, order_by=None, order_desc=True) -> list:
        params = f"select=*&limit={limit}"
        if filter_by:
            col, val = filter_by
            params += f"&{col}=eq.{urllib.parse.quote(str(val))}"
        if order_by:
            direction = "desc" if order_desc else "asc"
            params += f"&order={order_by}.{direction}"
        return self._get(table_name, params)

    def insert_dataframe(self, frame: pd.DataFrame, table_name: str):
        rows = frame.reset_index(drop=True).to_dict(orient="records")
        rows = [{str(k).lower(): v for k, v in row.items()} for row in rows]
        for row in rows:
            try:
                self._post(table_name, [row])
            except Exception as e:
                print(str(e))

    def insert_data_frame_one_shot(self, frame: pd.DataFrame, table_name: str):
        try:
            self._post(table_name, frame.to_dict(orient="records"))
        except Exception as e:
            print(str(e))

    def insert_json_array(self, json_objs: list, table_name: str):
        for obj in json_objs:
            try:
                self._post(table_name, [obj])
            except Exception as e:
                print(str(e))

    def update_given_dataframe(self, frame: pd.DataFrame, table_name: str, eq_column: str, eq_row_name: str):
        rows = frame.reset_index(drop=True).to_dict(orient="records")
        for row in rows:
            row = {str(k).lower(): v for k, v in row.items()}
            try:
                self._patch(table_name, eq_column, row[eq_row_name], row)
            except Exception as e:
                print(str(e))

    def delete_equal_to(self, table_name: str, column_equal_name: str, value):
        return self._delete(table_name, f"{column_equal_name}=eq.{urllib.parse.quote(str(value))}")

    def delete_where_colum_is_not_null(self, table_name: str, column_name: str):
        return self._delete(table_name, f"{column_name}=not.is.null")

    def rpc(self, rpc_name: str, rpc_body: dict):
        r = self.session.post(f"{self._url}/rest/v1/rpc/{rpc_name}", json=rpc_body)
        r.raise_for_status()
        return r.json()

    def update_clients(self):
        return self.rpc("update_materialized_views", {})

    def clear_tes_operation(self):
        return self.rpc("delete_repeated_raw", {"f_var_name": ""})

    def clear_tes_operations_from_date(self, today_date: str):
        return self.rpc("delete_tes_operations_of_date", {"date_to_use": today_date})

    def cleat_tes_operations_given_date_tes(self, today_date: str, tes_name: str):
        return self.rpc("delete_tes_operations_of_date_and_tes",
                        {"date_to_use": today_date, "tes_name": tes_name})
