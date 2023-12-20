#import sys
#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from datetime import datetime
from utilities.colombia_calendar import calendar_colombia
from utilities.date_functions import datetime_to_ql,ql_to_datetime
from utilities.colombia_calendar import calendar_colombia
from bond_functions.tes_quant_lib_details import tes_quantlib_det
import pandas as pd
import QuantLib as ql
import pandas as pd

from datetime import datetime

import numpy_financial as npf
import pandas as pd


class Loan:
    def __init__(self, term_years, interest_rate, original_balance, start_date):
        """
        Initializes a Loan object.

        Parameters:
        - term_years (int): The loan term in years.
        - interest_rate (float): The annual simple interest rate.
        - original_balance (float): The initial loan amount.
        - start_date (datetime): The start date of the loan.
        """
        self.term_years = term_years
        self.interest_rate = interest_rate
        self.original_balance = original_balance
        self.start_date = start_date
        self.start_date_ql = datetime_to_ql(self.start_date)

    def calculate_monthly_payment(self):
        """
        Calculates the monthly payment for the loan.

        Returns:
        - float: The calculated monthly payment.
        """
        monthly_interest_rate = self.interest_rate / 12 / 100
        num_payments = self.term_years * 12
        monthly_payment = npf.pmt(monthly_interest_rate, num_payments, -self.original_balance)
        return monthly_payment

    def generate_cash_flow_table(self):
        """
        Generates a cash flow table for the loan.

        Returns:
        - pd.DataFrame: A DataFrame containing the cash flow details.
        """
        monthly_payment = self.calculate_monthly_payment()
        periods = list(range(1, self.term_years * 12 + 1))

        interest_payment = []
        principal_payment = []
        ending_balance = []

        current_balance = self.original_balance
        for i in range(len(periods)):
            interest_payment.append(current_balance * (self.interest_rate / 100 / 12))
            principal_payment.append(monthly_payment - interest_payment[-1])
            ending_balance.append(current_balance - principal_payment[-1])

            current_balance = ending_balance[-1]

        date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
        date_list = [ql_to_datetime(ql_date) for ql_date in date_list]
        cf_data = {
            'Date': date_list,
            'Interest': interest_payment,
            'Principal': principal_payment,
            'Payment': [monthly_payment] * len(periods),
            'Ending Balance': ending_balance,
            'Beginning Balance': [self.original_balance] + ending_balance[:-1]
        }

        cf_table = pd.DataFrame(data=cf_data, index=periods)
        cf_table = cf_table[['Date', 'Beginning Balance', 'Payment', 'Interest', 'Principal', 'Ending Balance']]

        return cf_table


