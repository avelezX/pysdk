from swap_functions.ibr_swap_ql_functions import fwd_rates_generation
import pandas as pd


class Implicitas:

    def __init__(self, ibr_quotes, interval_tenor, start_date):
        self.ibr_quotes = pd.DataFrame(ibr_quotes)
        self.interval_tenor = interval_tenor
        self.start_date = start_date

    def rates_generation(self, curve, start_date, interval_period='m'):
        return fwd_rates_generation(
            curve=curve,
            start_date=start_date,
            inverval_tenor=self.interval_tenor,
            interval_period=interval_period
        )
