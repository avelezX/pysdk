#import sys
#sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from datetime import datetime
from utilities.colombia_calendar import calendar_colombia
from utilities.date_functions import datetime_to_ql
from utilities.colombia_calendar import calendar_colombia
from bond_functions.tes_quant_lib_details import tes_quantlib_det
import pandas as pd
import QuantLib as ql
import pandas as pd

class LoanStructure:
    def __init__(self, notional=None, emission=None, maturity=None, coupon=None):
        self.emission = emission
        self.maturity = maturity
        self.coupon = coupon
        self.notional = notional
        self.calendar = tes_quantlib_det['calendar']

    def ql_loan_structure(self):
        start_date = ql.Date(self.emission.day, self.emission.month, self.emission.year)
        maturity_date = ql.Date(self.maturity.day, self.maturity.month, self.maturity.year)

        schedule = ql.MakeSchedule(start_date, maturity_date, ql.Period('1M'))

        # Use a constant interest rate for simplicity
        rate = ql.SimpleQuote(self.coupon)
        rates = [ql.QuoteHandle(rate)]

        loan = ql.AmortizingFixedRateBond(0, self.notional, schedule, rates, ql.Thirty365)
        return loan
    # AmortizingFixedRateBond::AmortizingFixedRateBond(Integer,std::vector< Real,std::allocator< Real > > const &,Schedule const &,std::vector< InterestRate,std::allocator< InterestRate > > const &)
    def get_cashflows(self):
        # Get the cashflows
        loan=self.ql_loan_structure()
        cashflows = loan.cashflows()

        # Convert cash flows to a pandas DataFrame
        cashflows_df = pd.DataFrame([(cf.date(), cf.amount()) for cf in cashflows], columns=['Date', 'Amount'])
        
        # Display cash flows in a table
        print(cashflows_df)

