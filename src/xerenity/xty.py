import os
from supabase import Client
from supabase import create_client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

load_dotenv()

class Xerenity:

    def __init__(self, username, password, auto_refresh: bool = False):
        url: str = os.getenv('XTY_URL')
        key: str = os.getenv('XTY_TOKEN')
        opts = ClientOptions(auto_refresh_token=auto_refresh).replace(schema="xerenity")

        self.session: Client = create_client(url, key, options=opts)

        self.session.auth.sign_in_with_password(
            {
                "email": username,
                "password": password
            }
        )

    def log_out(self) -> None:
        """

        Logs out user from current session
        https://supabase.com/docs/reference/python/auth-signout
        :return: None
        """

        self.session.auth.sign_out()

    def read_table(self, table_name):
        """

        Retrieves all data from a given source
        :param table_name: table source to be read from
        :return:
        """
        return self.session.table(table_name=table_name).select('*').execute()

    def read_last_entry(self, table_name, colum_name):
        """

        :param table_name:
        :return:
        """

        return self.session.table(table_name=table_name).select('*').order(colum_name).limit(1)
