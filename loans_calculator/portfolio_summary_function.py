import pandas as pd
from datetime import datetime
from server.loan_calculator.loan_calculator import LoanCalculatorServer
from utilities.date_functions import datetime_to_ql, ql_to_datetime
from loans_calculator.funciones_analisis_credito import create_cashflows_and_total_value
import numpy as np


class LoanPortfolioAnalyzer:
    def __init__(self, all_loan_data, filter_date):
        self.bank_df = None
        self.filter_date = filter_date
        self.value_date_dt = None
        self.all_loans_data = all_loan_data
        self.results = {}
        self.bank_data = {}
        self.loan_ids_list = []
        self.total_value_sum = 0
        self.accrued_interest_sum = 0
        self.total_loan_count = 0
        self.total_average_irr = 0
        self.total_average_duration = 0
        self.total_average_tenor = 0
        self.total_value_fija_sum = 0
        self.total_value_ibr_sum = 0
        self.total_average_tenor = 0
        self.outdated_loan_count = 0
        self.weighted_irr_fija_sum = 0
        self.weighted_irr_ibr_sum = 0
        self.weighted_irr_sum = 0
        self.weighted_duration_sum = 0
        self.weighted_tenor_sum = 0
        self.total_weighted_irr_sum = 0
        self.total_average_irr_fija = 0
        self.total_value_ibr_sum = 0
        self.total_average_irr_ibr = 0
        self.total_weighted_duration_sum = 0
        self.not_calculated_loan_ids = []
        self.not_calculated_loan_count = 0

    def retrieve_data(self):
        self.value_date = datetime_to_ql(datetime.strptime(self.filter_date, '%Y-%m-%d'))
        self.value_date_dt = ql_to_datetime(self.value_date)
        self.db_info = self.all_loans_data['db_info']

    def process_loans(self):
        for i, loan in enumerate(self.all_loans_data['loans']):
            try:
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
            except Exception as e:
                print('Error en la cargada de un credito, no se tendra en cuenta')

    def aggregate_data(self):

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

            self.loan_ids_list.append(loan_id)

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
                print(
                    f"total_value={total_value}, accrued_interest={accrued_interest}, irr={irr}, duration={duration}, tenor={tenor}, bank={bank}")
                self.not_calculated_loan_count += 1
                continue

            if not (start_date < self.value_date_dt < last_payment):
                self.outdated_loan_count += 1
                continue

            self.total_value_sum += total_value
            self.accrued_interest_sum += accrued_interest
            self.total_loan_count += 1

            self.bank_data[bank]['total_value'] += total_value
            self.bank_data[bank]['weighted_irr_sum'] += irr * total_value
            self.bank_data[bank]['accrued_interest'] += accrued_interest
            self.bank_data[bank]['weighted_duration_sum'] += duration * total_value
            self.bank_data[bank]['weighted_tenor_sum'] += tenor * total_value
            self.bank_data[bank]['loan_count'] += 1

            if loan_type == 'fija':
                self.total_value_fija_sum += total_value
                self.bank_data[bank]['total_value_fija'] += total_value
                self.bank_data[bank]['weighted_irr_fija_sum'] += irr * total_value
            elif loan_type == 'ibr':
                self.total_value_ibr_sum += total_value
                self.bank_data[bank]['total_value_ibr'] += total_value
                self.bank_data[bank]['weighted_irr_ibr_sum'] += irr * total_value

            self.bank_data[bank]['loan_ids'].append(loan_id)

        # Assign the accumulated loan_ids_list after the loop

        for bank, data in self.bank_data.items():
            data['average_irr'] = data['weighted_irr_sum'] / data['total_value'] if data['total_value'] > 0 else None
            data['average_duration'] = data['weighted_duration_sum'] / data['total_value'] if data[
                                                                                                  'total_value'] > 0 else None
            data['average_tenor'] = data['weighted_tenor_sum'] / data['total_value'] if data[
                                                                                            'total_value'] > 0 else None
            data['average_irr_fija'] = (data['weighted_irr_fija_sum'] / data['total_value_fija']
                                        if data['total_value_fija'] > 0 else None)
            data['average_irr_ibr'] = (data['weighted_irr_ibr_sum'] / data['total_value_ibr']
                                       if data['total_value_ibr'] > 0 else None)

    def calculate_weighted_averages(self):
        self.bank_df = pd.DataFrame.from_dict(self.bank_data, orient='index')

        self.total_value_sum = self.bank_df['total_value'].sum()
        self.total_value_fija_sum = self.bank_df['total_value_fija'].sum()
        self.total_value_ibr_sum = self.bank_df['total_value_ibr'].sum()

        self.weighted_irr_fija_sum = self.bank_df['weighted_irr_fija_sum'].sum()
        self.weighted_irr_ibr_sum = self.bank_df['weighted_irr_ibr_sum'].sum()
        self.total_weighted_irr_sum = self.bank_df['weighted_irr_sum'].sum()
        self.total_weighted_duration_sum = self.bank_df['weighted_duration_sum'].sum()
        self.total_weighted_tenor_sum = self.bank_df['weighted_tenor_sum'].sum()

        self.total_average_irr = (
                self.total_weighted_irr_sum / self.total_value_sum) if self.total_value_sum > 0 else None
        self.total_average_duration = (
                self.total_weighted_duration_sum / self.total_value_sum) if self.total_value_sum > 0 else None
        self.total_average_tenor = (
                self.total_weighted_tenor_sum / self.total_value_sum) if self.total_value_sum > 0 else None
        self.total_average_irr_fija = (
                self.weighted_irr_fija_sum / self.total_value_fija_sum) if self.total_value_fija_sum > 0 else None
        self.total_average_irr_ibr = (
                self.weighted_irr_ibr_sum / self.total_value_ibr_sum) if self.total_value_ibr_sum > 0 else None

        self.accrued_interest_sum = self.bank_df['accrued_interest'].sum()

    def get_final_dataframe(self):

        totals = pd.DataFrame.from_dict({
            'total_value': [self.total_value_sum],
            'accrued_interest': [self.accrued_interest_sum],
            'weighted_irr_sum': [self.total_weighted_irr_sum],
            'average_irr': [self.total_average_irr],
            'average_duration': [self.total_average_duration],
            'average_tenor': [self.total_average_tenor],
            'loan_count': [self.total_loan_count],
            'outdated_loan_count': [self.outdated_loan_count],
            'total_value_fija': [self.total_value_fija_sum],
            'average_irr_fija': [self.total_average_irr_fija],
            'total_value_ibr': [self.total_value_ibr_sum],
            'average_irr_ibr': [self.total_average_irr_ibr],
            'not_calculated_loan_count': [self.not_calculated_loan_count],
            'loan_ids': [self.loan_ids_list]
        })

        self.final_df = pd.concat([self.bank_df, totals])
        self.final_df = self.final_df[
            ['total_value', 'accrued_interest', 'average_irr', 'average_duration', 'average_tenor', 'loan_count',
             'outdated_loan_count', 'total_value_fija', 'average_irr_fija', 'total_value_ibr', 'average_irr_ibr',
             'not_calculated_loan_count', 'loan_ids']]
        self.final_df.fillna(value=0, inplace=True)

        return self.final_df.sort_values(by='total_value', ascending=False)
