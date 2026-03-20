import requests
from html.parser import HTMLParser
from data_collectors.DataCollector import DataCollector
from html.entities import name2codepoint
from datetime import datetime, date
import pandas as pd
import calendar
import string
import unicodedata


class SenParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.num_table = 2

        self.table_rows = []

        self.current_row = []

        self.collecting = False

        self.headers = []

        self.collected_rows = 0

        self.current_date = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.num_table -= 1

        if self.num_table == 0:
            self.collecting = True

    def handle_endtag(self, tag):
        if tag == 'tr':

            if len(self.current_row) > 0:
                self.table_rows.append(self.current_row)
                self.current_row = []

    def handle_data(self, data):

        if 'Cierres:' in data:
            data = ''.join((c for c in unicodedata.normalize('NFD', data) if unicodedata.category(c) != 'Mn'))
            data = data.lower()
            # Here is the data
            months = {
                'enero': 1,
                'febrero': 2,
                'marzo': 3,
                'abril': 4,
                'mayo': 5,
                'junio': 6,
                'julio': 7,
                'agosto': 8,
                'septiembre': 9,
                'octubre': 10,
                'noviembre': 11,
                'diciembre': 12
            }
            for x in string.punctuation + '\t\n\r\v\f':
                data = data.replace(x, '')
            remove = [
                ('hasta', ''),
                ('de', ''),
                ('cierres', ''),
                ('lunes', ''),
                ('martes', ''),
                ('miercoles', ''),
                ('jueves', ''),
                ('viernes', ''),
                ('sabado', ''),
                ('doming', ''),
            ]

            for r in remove:
                data = data.replace(*r)

            month = None

            data = data.split(" ")
            valid = []
            for date_piece in data:
                if len(date_piece) > 0:
                    if date_piece in months:
                        month = months.get(date_piece)
                    else:
                        valid.append(date_piece)

            day = int(valid[0])
            year = int(valid[1])

            self.current_date = datetime(year=year, month=month, day=day)

        if self.collecting:

            if self.collected_rows > 0:
                if data != '\n':
                    data = data.replace('.', '')
                    data = data.replace(',', '.')
                    try:
                        self.current_row.append(float(data))
                    except:
                        try:
                            time_obj = datetime.strptime(data, '%H:%M:%S')

                            result = self.current_date.replace(
                                hour=time_obj.hour,
                                minute=time_obj.minute,
                                second=time_obj.second,
                                microsecond=0
                            )

                            self.current_row.append(result)

                        except:
                            pass

            self.collected_rows += 1


class Sen(DataCollector):
    def __init__(self):
        super().__init__(name='sen')

        self.sen_url = 'http://quimbaya.banrep.gov.co/sistema-financiero/cierres-sen/CONH/{}.htm'

        self.has_intra_day_prices = True

    def get_stock_price(self, symbol: str, from_date=datetime.today().strftime('%Y-%m-%d'),
                        to_date=datetime.today().strftime('%Y-%m-%d')):
        final_url = self.sen_url.format(symbol)

        sen_response = requests.get(final_url)

        parser = SenParser()
        parser.feed(sen_response.text)

        self.pure_dataframe = pd.DataFrame(parser.table_rows, columns=['Date', 'Price', 'Yield', 'Volume'])

        close_date = self.pure_dataframe["Date"].max()

        operation_date = close_date.strftime('%Y-%m-%d')

        self.pure_dataframe['Date'] = self.pure_dataframe['Date'].apply(datetime.strftime, format='%Y-%m-%d %H:%M:%S')

        # Date   Open       High        Low      Close  Adj Close   Volume
        resul = pd.DataFrame({
            'Date': [operation_date],
            'Open': self.pure_dataframe.loc[self.pure_dataframe['Date'].idxmin(), 'Yield'],
            'High': self.pure_dataframe['Yield'].max(),
            'Low': self.pure_dataframe['Yield'].min(),
            'Close': self.pure_dataframe.loc[self.pure_dataframe['Date'].idxmax(), 'Yield'],
            'Adj Close': None,
            'Volume': self.pure_dataframe['Volume'].sum()
        })

        return resul, operation_date


def get_multiple_stock_price(self, symbol: list, date):
    pass
