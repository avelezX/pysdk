import json
from datetime import datetime
from financial_variables.FinancialVariables import FinancialVariables
from db_connection.supabase.Client import SupabaseConnection
from financial_variables.list_all_fvars import all_local_fvars

from dateutil import parser

def collect_intra_prices():
    connection = SupabaseConnection()

    connection.sign_in_as_collector()

    for index, row in all_local_fvars():
        fvar = FinancialVariables(
            name=row['name'],
            type=row['type'],
            country=row['country'],
            collector_data=json.loads(row['collector']),
            supabase=connection.supabase
        )

        try:
            _, operation_date = fvar.live_prices('sen')

            aux = connection.get_last_by(
                table_name='tes_operation',
                filter_by=('tes', fvar.name.lower()),
                column_name='date'
            )

            print('------------storing-----------')

            if len(aux) > 0:
                filter_date = parser.parse(aux[0]['date'])
                filtering = fvar.raw_values[fvar.raw_values['Date'] > str(filter_date)].copy(deep=True)
            else:
                filtering = fvar.raw_values.copy(deep=True)


            fvar.insert_dataframe(frame=filtering, raw=True)

            print('Stored in {} number of rows {}'.format(fvar.name, len(filtering)))

        except Exception as error:
            print("Could not retrieve financial variable {}".format(str(error)))
