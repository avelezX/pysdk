# %%
import sys
sys.path.append("/Users/andre/Documents/xerenity/pysdk")
from utilities.date_functions import datetime_to_ql, ql_to_datetime
import QuantLib as ql
import pandas as pd
import datetime

class Loan_test:

    # Mapping from periodicity to its numerical value
    number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1 / 4, 'Bimensual': 1 / 6, 'Mensual': 1 / 12}

    # List of acceptable methods for counting days
    count_days_values = ['por_dias_360', 'por_dias_36   5', 'por_periodo']

    def __init__(self,
                 interest_rate,
                 periodicity,
                 number_of_payments,
                 start_date,
                 original_balance,
                 rate_type='fixed',
                 days_count=None,
                 grace_type=None,
                 grace_period=None,
                 db_info=None):
        """
        Generates cash flow table with IBR rates.
        
        Parameters:
        - value_date (datetime): Date for valuation.
        - curve: IBR curve.
        - tipo_de_cobro (str): Type of charge ('por_dias_360', 'por_dias_365', 'por_periodo').
        - periodicidad_tasa (str): Rate periodicity ('SV', 'TV', 'MV').
        - grace_type (str): Type of grace period ('capital', 'interest', 'ambos').
        - grace_period (int): Length of grace period in months.

        Returns:
        - pd.DataFrame: A DataFrame containing the cash flow details.
        """

        self.periodicity = periodicity
        self.number_of_payments = number_of_payments
        self.interest_rate = interest_rate
        self.original_balance = original_balance
        self.start_date = start_date
        self.start_date_ql = datetime_to_ql(self.start_date)
        self.rate_type = rate_type
        self.db_info = db_info
        self.days_count = days_count
        self.grace_type = grace_type
        self.grace_period = grace_period
        self.grace_period_interest = self.grace_period if self.grace_type in ['interest', 'ambos'] else 0
        self.grace_period_principal = self.grace_period if self.grace_type in ['capital', 'ambos'] else 0
        self.capital_payments=self.number_of_payments-self.grace_period_principal


    def calculate_custom_period_payment(self):
        """
        Calculates the loan payment for a given periodicity.

        Parameters:
        - interest_rate (float): Annual interest rate as a percentage.
        - num_payments (int): Total number of payments.
        - original_balance (float): The loan amount.
        - periodicity (int): Number of payments per year (e.g., 12 for monthly, 6 for bimonthly, 4 for quarterly, 1 for yearly).

        Returns:
        - float: The calculated loan payment.
        """
        annual_interest_rate = self.interest_rate / 100
        periodic_interest_rate = annual_interest_rate / (1 / self.number_to_user[self.periodicity])

        discount_factor = ((1 + periodic_interest_rate) ** self.capital_payments - 1) / (
                periodic_interest_rate * (1 + periodic_interest_rate) ** self.capital_payments)
        
        payment = self.original_balance / discount_factor
        
        return payment


    def generate_cash_flow_table(self):
        """
        Generates a cash flow table for the loan.

        Returns:
        - pd.DataFrame: A DataFrame containing the cash flow details.
        """
        monthly_payment = self.calculate_custom_period_payment()
        periods = list(range(1, self.number_of_payments + 1))

        interest_payment = []
        principal_payment = []
        ending_balance = []
        date_list = []
        payment=[]
        current_balance = self.original_balance

        acumulated_interest = 0

        for i in range(len(periods)):
            date_list.append(
                self.start_date_ql + ql.Period(int((i + 1) * (12 * self.number_to_user[self.periodicity])), ql.Months))

            # Calculating interest payment
            if i < self.grace_period_interest:
                interest_payment.append(0)
                acumulated_interest += current_balance * (self.interest_rate / 100 * self.number_to_user[self.periodicity])
            else:
                interest_payment.append(current_balance * (self.interest_rate / 100 * self.number_to_user[self.periodicity]))

            # Calculating principal payment
            if i < self.grace_period_principal:
                principal_payment.append(0)  # No principal payment during grace period
                ending_balance.append(current_balance)  # Balance remains unchanged during grace period
            else:
                principal_payment.append(monthly_payment - interest_payment[-1])  # Principal payment is the remainder
                ending_balance.append(current_balance - principal_payment[-1])  # Update balance after principal payment

            payment.append(interest_payment[-1]+principal_payment[-1])
            current_balance = ending_balance[-1]

        date_list = [ql_to_datetime(ql_date) for ql_date in date_list]
        cf_data = {
            'date': date_list,
            'interest': interest_payment,
            'rate': self.interest_rate,
            'principal': principal_payment,
            'payment': payment,
            'ending_balance': ending_balance,
            'beginning_balance': [self.original_balance] + ending_balance[:-1]
        }

        cf_table = pd.DataFrame(data=cf_data, index=periods)
        cf_table = cf_table[['date', 'beginning_balance', 'rate', 'payment', 'interest', 'principal', 'ending_balance']]

        return cf_table
    # %%
