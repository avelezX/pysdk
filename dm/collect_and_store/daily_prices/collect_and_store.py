import json
import pandas as pd
from financial_variables.FinancialVariables import FinancialVariables
from db_connection.supabase.Client import SupabaseConnection

from financial_variables.list_all_fvars import all_local_fvars


def collect_daily_prices():
    connection = SupabaseConnection()

    connection.sign_is_as_user(user_name="svelezsaffon@gmail.com", password="Loquita1053778047")

    for index, row in all_local_fvars():

        fvar = FinancialVariables(
            name=row['name'],
            type=row['type'],
            country=row['country'],
            collector_data=json.loads(row['collector']),
            supabase=connection.supabase
        )

        try:

            frame = fvar.live_prices('sen')

            fvar.insert_dataframe(frame=frame, raw=False)

            print("Stored {}".format(row['name']))
        except Exception as error:
            print("Could not retrieve financial variable {}".format(str(error)))

        try:
            fvar.delete_repeated(raw=False)
            print("Cleaned up financial variable {}".format(row['name']))
        except Exception as error:
            print("Could not retrieve financial variable {}".format(str(error)))
