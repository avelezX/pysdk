from utilities.date_functions import datetime_to_ql
import pandas as pd

from loan.helperFunctions import QlHelperFunctions


class Loan:
    number_to_user = {
        'Anual': 1,
        'Semestral': 0.5,
        'Trimestral': 1 / 4,
        'Bimensual': 1 / 6,
        'Mensual': 1 / 12
    }
    count_days_values = [
        'por_dias_360',
        'por_dias_365',
        'por_periodo'
    ]

    user_to_spanish_periodo = {
        'Anual': 'ibr_12m',
        'Semestral': 'ibr_6m',
        'Trimestral': 'ibr_3m',
        'Mensual': 'ibr_1m'
    }

    def __init__(self,
                 id,
                 owner,
                 type,
                 interest_rate,
                 periodicity,
                 number_of_payments,
                 start_date,
                 original_balance,
                 rate_type='fixed',
                 days_count=None,
                 grace_type=None,
                 grace_period=None,
                 db_info=None,
                 min_period_rate=None,
                 loan_identifier=None,
                 bank=None):
        
        self.id=id
        self.owner=owner
        self.type=type
        self.periodicity = periodicity
        self.periodicity_spanish = self.user_to_spanish_periodo[self.periodicity]
        self.number_of_payments = number_of_payments
        self.interest_rate = interest_rate
        self.original_balance = original_balance
        self.start_date = start_date
        self.start_date_ql = datetime_to_ql(self.start_date)
        self.rate_type = rate_type
        self.db_info = pd.DataFrame(db_info)
        self.days_count = days_count
        self.grace_type = grace_type
        self.grace_period = float(grace_period) if grace_period is not None else 0
        self.grace_period_interest = self.grace_period if self.grace_type in ['interest', 'ambos'] else 0
        self.grace_period_principal = self.grace_period if self.grace_type in ['capital', 'ambos'] else 0
        self.capital_payments = self.number_of_payments - self.grace_period_principal
        self.min_period_rate = min_period_rate if min_period_rate is not None else 0
        self.qlHelper = QlHelperFunctions()
        self.loan_identifier=loan_identifier
        self.banco=bank

    def calculate_custom_period_payment(self):
        """
        Calculates the loan payment for a given periodicity.
        Includes robust handling for very small interest rates.
        """
        annual_interest_rate = self.interest_rate / 100
        periodic_interest_rate = annual_interest_rate / (1 / self.number_to_user[self.periodicity])
        # Handle zero or very small interest rate case (tolerance for floating-point precision)
        tolerance = 1e-10
        if abs(periodic_interest_rate) < tolerance:
            # With 0% interest, payment is simply principal divided by number of payments
            discount_factor = self.capital_payments
        else:
            # Standard present value annuity factor formula
            discount_factor = ((1 + periodic_interest_rate) ** self.capital_payments - 1) / (
                    periodic_interest_rate * (1 + periodic_interest_rate) ** self.capital_payments)

        if abs(discount_factor) < tolerance:
            return self.original_balance

        return self.original_balance / discount_factor

    def generate_cash_flow(self, value_date=None, uvr=None):
        pass
