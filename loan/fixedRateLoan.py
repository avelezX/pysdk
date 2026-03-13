from loan.Loan import Loan
import QuantLib as ql
import pandas as pd
from utilities.date_functions import ql_to_datetime


class FixedRateLoan(Loan):
    def generate_cash_flow(self, value_date=None, uvr: bool = None):
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
        payment = []
        current_balance = self.original_balance

        acumulated_interest = 0

        for i in range(len(periods)):
            date_list.append(
                self.start_date_ql + ql.Period(int((i + 1) * (12 * self.number_to_user[self.periodicity])), ql.Months))

            # Calculating interest payment
            if i < self.grace_period_interest:
                interest_payment.append(0)
                acumulated_interest += current_balance * (
                        self.interest_rate / 100 * self.number_to_user[self.periodicity])
            else:
                interest_payment.append(
                    current_balance * (self.interest_rate / 100 * self.number_to_user[self.periodicity]))

            # Calculating principal payment
            if i < self.grace_period_principal:
                principal_payment.append(0)  # No principal payment during grace period
                ending_balance.append(current_balance)  # Balance remains unchanged during grace period
            else:
                principal_payment.append(monthly_payment - interest_payment[-1])  # Principal payment is the remainder
                ending_balance.append(current_balance - principal_payment[-1])  # Update balance after principal payment

            payment.append(interest_payment[-1] + principal_payment[-1])
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


        if uvr:
            self.db_info['fecha'] = pd.to_datetime(self.db_info['fecha'])

            # Get intersection of dates
            date_set = set(date_list)
            df_date_set = set(self.db_info['fecha'])
            intersected_dates = date_set.intersection(df_date_set)

            # Filter DataFrame
            intersection_df = self.db_info[self.db_info['fecha'].isin(intersected_dates)]

            merged_df = cf_table.merge(intersection_df, left_on='date', right_on='fecha', how='left')

            # Define columns to multiply (all except the date columns)
            columns_to_multiply = ['interest', 'principal', 'payment', 'ending_balance', 'beginning_balance']

            # Multiply each column by the valor
            for col in columns_to_multiply:
                merged_df[col] = merged_df[col] * merged_df['valor']

            cf_table = merged_df.copy()

        cf_table = cf_table[['date', 'beginning_balance', 'rate', 'payment', 'interest', 'principal', 'ending_balance']]

        print(pd.DataFrame(data=cf_table, index=periods))

        return cf_table
