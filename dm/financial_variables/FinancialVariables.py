import json

import pandas as pd

from data_collectors.CollectorCreator import CollectorCreator
from datetime import datetime


class FinancialVariables:

    def __init__(self,
                 name,
                 collector_data: dict = None,
                 type=None,
                 country=None,
                 extra_data=None,
                 supabase=None
                 ):
        self.name = name

        self.type = type

        self.country = country

        self.collectors = {}

        self.id_in_collector = {}

        self.raw_values = pd.DataFrame(None)

        self.extra_data = extra_data

        self.supabase = supabase

        if collector_data is None:

            readed_pd = pd.read_csv('/Users/avelezxerenity/xdb/financial_variables/fvars.tsv', delimiter='\t+',
                                    engine='python')

            collector_data = json.loads(readed_pd[readed_pd['name'] == self.name]['collector'][0])

            if collector_data is None:
                raise Exception("This collector cant be created even from the csv file")

        for collector_name, ticker in collector_data.items():
            self.collectors[collector_name] = CollectorCreator().create(name=collector_name)
            self.id_in_collector[collector_name] = ticker

    def static_data(self):
        return self.extra_data

    def list_all_f_vars(self):
        cursor = self.db.get_cursor()
        rows = []
        cursor.execute("SELECT * FROM finacial_variables")

        for row in cursor.fetchall():
            rows.append(row)

        return rows

    def insert_f_var(self):

        if self.db is None:
            raise Exception("A database conenction is needed")

        cursor = self.db.get_cursor()

        sql = """
        IF NOT EXISTS (SELECT * FROM finacial_variables WHERE Name = '{}')
        BEGIN
            INSERT INTO finacial_variables (Name,Type,Periodicity,Ticker,Country) VALUES (?,?,?,?,?)
        END
        """.format(self.name)

        cursor.execute(
            sql,
            self.name,
            self.type,
            # self.periodicity,
            self.ticker,
            self.country
        )
        self.db.connection.commit()

    def insert_dataframe(self, frame, raw=False):
        if self.supabase is None:
            raise Exception("A database connection is needed")

        frame = frame.reset_index()

        for row_dict in frame.to_dict(orient="records"):
            if 'Adj Close' in row_dict:
                del row_dict['Adj Close']

            del row_dict['index']
            new_keys = {
                "tes": str(self.name).lower(),
                "collector": "sen"
            }
            for ukey, uval in row_dict.items():
                new_keys[str(ukey).lower()] = uval

            self.supabase.table('tes_operation').insert(new_keys).execute()

    def calculate_ticker(self, collector: str):
        if collector not in self.collectors:
            msg = "Collector {} not found in {}".format(collector, self.name)
            raise Exception(msg)

        if collector not in self.id_in_collector:
            msg = "Ticker not found with collector {} not found in {}".format(collector, self.name)
            raise Exception(msg)

        return self.id_in_collector[collector]

    def historical_prices(self, raw=False):
        if self.supabase is None:
            raise Exception("A database connection is needed")

        if raw:
            real_table_name = "{}_RAW".format(self.name)
        else:
            real_table_name = self.name

        response = self.supabase.table(real_table_name.lower()).select("*").execute()

        return pd.DataFrame(response.data)

    def live_prices(self, collector_name: str,
                    from_date=datetime.today().strftime('%Y-%m-%d'),
                    to_date=datetime.today().strftime('%Y-%m-%d')):

        id_ticker = self.calculate_ticker(collector=collector_name)

        collector = self.collectors[collector_name]

        all_frame, operation_date = collector.get_stock_price(symbol=id_ticker, from_date=from_date, to_date=to_date)

        self.raw_values = collector.pure_dataframe

        return all_frame, operation_date

    def historical_size(self, raw=False):

        if raw:
            real_table_name = "{}_RAW".format(self.name)
        else:
            real_table_name = self.name

        return self.supabase.rpc('data_size', {'f_var_name': real_table_name.lower()}).execute().data

    def delete_repeated(self, raw=False):
        return self.supabase.rpc('delete_repeated_raw', {'f_var_name': ""}).execute().data
