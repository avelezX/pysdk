import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
import numpy as np
import numpy_financial as npf
from scipy.optimize import newton
import os
import json
import pandas as pd
import QuantLib as ql
from datetime import datetime
from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer
from utilities.date_functions import datetime_to_ql, ql_to_datetime, calculate_irr
from loans_calculator.funciones_analisis_credito import merge_two_resulting_cashflows, create_cashflows_and_total_value, calculate_debt_duration

class LoanPortfolioAnalyzer:
    def __init__(self, xerenity_user, xerenity_pwd, filter_date):
        self.xty = Xerenity(username=xerenity_user, password=xerenity_pwd)
        self.filter_date = filter_date
        self.value_date_dt = None
        self.all_loans_data = None
        self.results = {}
        self.bank_data = {}

    def retrieve_data(self):
        self.all_loans_data = self.xty.get_all_loan_data(filter_date=self.filter_date)
        self.value_date = datetime_to_ql(datetime.strptime(self.filter_date, '%Y-%m-%d'))
        self.value_date_dt = ql_to_datetime(self.value_date)
        self.db_info = self.all_loans_data['db_info']

    def process_loans(self):
        for i, loan in enumerate(self.all_loans_data['loans']):
            loan_temp = loan.copy()
            loan_temp['db_info'] = self.db_info
            calc = LoanCalculatorServer(loan_temp, local_dev=True)
            loan_payments = calc.cash_flow_ibr()

            variables = create_cashflows_and_total_value(
                pd.DataFrame(loan_payments),
                self.value_date,
                datetime.strptime(loan['start_date'], '%Y-%m-%d'),
                {'por_dias_360': '30/360', 'por_dias_365': 'actual/365'}[loan['days_count']]
            )

            loan_temp.pop('db_info', None)
            self.results[f'loan_{i}'] = {
                'variables': variables,
                'loan_data': loan_temp
            }

    def aggregate_data(self):
        total_value_sum = 0
        accrued_interest_sum = 0
        total_loan_count = 0
        outdated_loan_count = 0
        not_calculated_loan_count = 0
        total_value_fija_sum = 0
        total_value_ibr_sum = 0
        weighted_irr_fija_sum = 0
        weighted_irr_ibr_sum = 0
        weighted_irr_sum = 0
        weighted_duration_sum = 0
        weighted_tenor_sum = 0
        loan_ids_list = []

        for loan_id, loan_info in self.results.items():
            total_value = loan_info['variables'].get('total_value')
            accrued_interest = loan_info['variables'].get('accrued_interest')
            irr = loan_info['variables'].get('irr')
            duration = loan_info['variables'].get('duration')
            tenor = loan_info['variables'].get('tenor')
            last_payment = loan_info['variables'].get('last_payment')
            start_date = loan_info['loan_data'].get('start_date')
            bank = loan_info['loan_data'].get('bank')
            loan_type = loan_info['loan_data'].get('type')
            loan_id = loan_info['loan_data'].get('id')

            loan_ids_list.append(loan_id)

            if bank not in self.bank_data:
                self.bank_data[bank] = {
                    'total_value': 0,
                    'weighted_irr_sum': 0,
                    'accrued_interest': 0,
                    'weighted_duration_sum': 0,
                    'weighted_tenor_sum': 0,
                    'loan_count': 0,
                    'outdated_loan_count': 0,
                    'total_value_fija': 0,
                    'weighted_irr_fija_sum': 0,
                    'total_value_ibr': 0,
                    'weighted_irr_ibr_sum': 0,
                    'loan_ids': []
                }

            if pd.isna(total_value) or pd.isna(accrued_interest) or pd.isna(irr) or pd.isna(duration) or pd.isna(tenor):
                print(f"Warning: Missing data detected in loan {loan_id}:")
                print(f"total_value={total_value}, accrued_interest={accrued_interest}, irr={irr}, duration={duration}, tenor={tenor}, bank={bank}")
                not_calculated_loan_count += 1
                continue

            if not (start_date < self.value_date_dt < last_payment):
                outdated_loan_count += 1
                continue

            total_value_sum += total_value
            accrued_interest_sum += accrued_interest
            total_loan_count += 1

            self.bank_data[bank]['total_value'] += total_value
            self.bank_data[bank]['weighted_irr_sum'] += irr * total_value
            self.bank_data[bank]['accrued_interest'] += accrued_interest
            self.bank_data[bank]['weighted_duration_sum'] += duration * total_value
            self.bank_data[bank]['weighted_tenor_sum'] += tenor * total_value
            self.bank_data[bank]['loan_count'] += 1

            if loan_type == 'fija':
                self.bank_data[bank]['total_value_fija'] += total_value
                self.bank_data[bank]['weighted_irr_fija_sum'] += irr * total_value
            elif loan_type == 'ibr':
                self.bank_data[bank]['total_value_ibr'] += total_value
                self.bank_data[bank]['weighted_irr_ibr_sum'] += irr * total_value

            self.bank_data[bank]['loan_ids'].append(loan_id)

        self._calculate_weighted_averages(total_value_sum)

    def _calculate_weighted_averages(self, total_value_sum):
        for bank, data in self.bank_data.items():
            data['average_irr'] = data['weighted_irr_sum'] / data['total_value'] if data['total_value'] > 0 else None
            data['average_duration'] = data['weighted_duration_sum'] / data['total_value'] if data['total_value'] > 0 else None
            data['average_tenor'] = data['weighted_tenor_sum'] / data['total_value'] if data['total_value'] > 0 else None
            data['average_irr_fija'] = (data['weighted_irr_fija_sum'] / data['total_value_fija']
                                        if data['total_value_fija'] > 0 else None)
            data['average_irr_ibr'] = (data['weighted_irr_ibr_sum'] / data['total_value_ibr']
                                       if data['total_value_ibr'] > 0 else None)
            data['loan_ids'] = json.dumps(data['loan_ids'])

        bank_df = pd.DataFrame.from_dict(self.bank_data, orient='index')

        total_value_fija_sum = bank_df['total_value_fija'].sum()
        total_value_ibr_sum = bank_df['total_value_ibr'].sum()
        weighted_irr_fija_sum = bank_df['weighted_irr_fija_sum'].sum()
        weighted_irr_ibr_sum = bank_df['weighted_irr_ibr_sum'].sum()
        total_weighted_irr_sum = bank_df['weighted_irr_sum'].sum()
        total_weighted_duration_sum = bank_df['weighted_duration_sum'].sum()
        total_weighted_tenor_sum = bank_df['weighted_tenor_sum'].sum()

        total_average_irr = (total_weighted_irr_sum / total_value_sum) if total_value_sum > 0 else None
        total_average_duration = (total_weighted_duration_sum / total_value_sum) if total_value_sum > 0 else None
        total_average_tenor = (total_weighted_tenor_sum / total_value_sum) if total_value_sum > 0 else None
        total_average_irr_fija = (weighted_irr_fija_sum / total_value_fija_sum) if total_value_fija_sum > 0 else None
        total_average_irr_ibr = (weighted_irr_ibr_sum / total_value_ibr_sum) if total_value_ibr_sum > 0 else None

        totals = pd.DataFrame({
            'total_value': [total_value_sum],
            'accrued_interest': [accrued_interest_sum],
            'weighted_irr_sum': [total_weighted_irr_sum],
            'average_irr': [total_average_irr],
            'average_duration': [total_average_duration],
            'average_tenor': [total_average_tenor],
            'loan_count': [total_loan_count],
            'outdated_loan_count': [outdated_loan_count],
            'total_value_fija': [total_value_fija_sum],
            'average_irr_fija': [total_average_irr_fija],
            'total_value_ibr': [total_value_ibr_sum],
            'average_irr_ibr': [total_average_irr_ibr],
            'not_calculated_loan_count': [not_calculated_loan_count],
            'loan_ids': [json.dumps(loan_ids_list)]
        }, index=['Total'])

        self.final_df = pd.concat([bank_df, totals])
        self.final_df = self.final_df[['total_value', 'accrued_interest', 'average_irr', 'average_duration', 'average_tenor', 'loan_count', 
                                       'outdated_loan_count', 'total_value_fija', 'average_irr_fija', 'total_value_ibr', 'average_irr_ibr',
                                       'not_calculated_loan_count', 'loan_ids']]
        self.final_df = self.final_df.sort_values(by='total_value', ascending=False)

    def get_final_dataframe(self):
        return self.final_df

# Example usage
if __name__ == "__main__":
    analyzer = LoanPortfolioAnalyzer(
        xerenity_user=os.getenv('XTY_USER'),
        xerenity_pwd=os.getenv('XTY_PWD'),
        filter_date="2024-09-14"
    )
    analyzer.retrieve_data()
    analyzer.process_loans()
    analyzer.aggregate_data()
    final_df = analyzer.get_final_dataframe()
    print(final_df)
