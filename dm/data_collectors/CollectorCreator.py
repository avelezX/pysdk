from data_collectors.sen.sen_data_collector import Sen
from data_collectors.fred.fred_data_collector import Fred
from data_collectors.yahoo.yahoo_data_collector import YahooExtractor


class CollectorCreator:

    def create(self, name):

        if name == "sen":
            return Sen()
        if name == "fred":
            return Fred()
        if name == "yahoo":
            return YahooExtractor()

        return None
