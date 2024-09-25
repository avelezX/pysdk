from loan.Loan import Loan
import QuantLib as ql
import pandas as pd
from utilities.date_functions import ql_to_datetime
import numpy as np

class IbrLoan(Loan):
    def generate_cash_flow(self, value_date=None, uvr=None):

        # Curve deberia ser una curva de IBR generada con la valoracion de la curva actual
        curve = self.qlHelper.create_curve(db_info=self.db_info,value_date=value_date)

        periodicidad_tasa = self.periodicity_spanish

        tipo_de_cobro = self.days_count

        number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1 / 4, 'Bimensual': 1 / 6, 'Mensual': 1 / 12}

        periodicidad_tasa_number = {
            'ibr_6m': 0.5,
            'ibr_3m': 1 / 4,
            'ibr_1m': 1 / 12,
            'ibr_12m': 1
        }

        periods = list(range(1, self.number_of_payments + 1))
        date_list = []
        start_date_ql = self.start_date_ql
        for i in range(len(periods)):
            date_list.append(
                start_date_ql + ql.Period(int((i + 1) * (12 * number_to_user[self.periodicity])), ql.Months))
        # return dates

        dates = date_list
        tasas = pd.DataFrame(self.db_info[periodicidad_tasa])
        # Convert 'fecha' column to datetime if it's not already in datetime format
        tasas['date'] = pd.to_datetime(self.db_info['fecha'])

        # Create a new DataFrame with 'your_date_list'
        result_data = {'date': dates}
        # Create an empty 'tasa' column in the result DataFrame
        result_data['rate'] = [None] * len(dates)

        result_df = pd.DataFrame(result_data)
        self.interest_rate = self.interest_rate
        self.min_period_rate = self.min_period_rate
        result_df['spread'] = self.interest_rate
        result_df['principal'] = 0  # self.original_balance / self.capital_payments

        # Iterate through each date in your_date_list
        moving_period = ql.Period(int(12 * number_to_user[self.periodicity]), ql.Months)
        result_df.at[0, 'beginning_balance'] = self.original_balance

        index_rows = ['date', 'beginning_balance', 'rate', 'rate_tot', 'payment', 'interest', 'principal',
                      'ending_balance']

        for i, date in enumerate(dates):
            # Find the closest date in the 'tasas' DataFrame
            if ql_to_datetime(date - moving_period) <= value_date:
                closest_date = tasas['date'].sub(pd.Timestamp(ql_to_datetime(date - moving_period))).abs().idxmin()
                # Assign the corresponding 'tasa' value to the result DataFrame
                closest_value = tasas.at[closest_date, periodicidad_tasa]
                result_df.at[i, 'rate'] = closest_value
                if self.min_period_rate is None:
                    result_df.at[i, 'rate_tot'] = result_df.at[i, 'rate'] + self.interest_rate
                else:
                    result_df.at[i, 'rate_tot'] = max(result_df.at[i, 'rate'] + self.interest_rate,
                                                      self.min_period_rate)
            # date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
            else:

                next_date = date + ql.Period(int(12 * periodicidad_tasa_number[periodicidad_tasa]), ql.Months)
                result_df.at[i, 'rate'] = curve.forwardRate(
                    date - moving_period,
                    next_date - moving_period,
                    ql.Actual360(), ql.Simple).rate() * 100
                if self.min_period_rate is None:
                    result_df.at[i, 'rate_tot'] = result_df.at[i, 'rate'] + self.interest_rate
                else:
                    result_df.at[i, 'rate_tot'] = max(result_df.at[i, 'rate'] + self.interest_rate,
                                                      self.min_period_rate)
            factor_cobro = 1

            if tipo_de_cobro == 'por_dias_360':
                # Calculate the actual number of days between the two dates
                # Usamos la periodicidad en pagos.
                p_pagos = self.number_to_user[self.periodicity]
                day_count = ql.Thirty360(ql.Thirty360.BondBasis)
                actual_days = day_count.dayCount(date, date + ql.Period(int(12 * p_pagos), ql.Months))
                factor_cobro = actual_days * (result_df.at[i, 'rate_tot']) / 360

            if tipo_de_cobro == 'por_dias_365':
                # Calculate the actual number of days between the two dates
                # Usamos la periodicidad en pagos.

                p_pagos = self.number_to_user[self.periodicity]
                day_count = ql.ActualActual(ql.ActualActual.ISDA)
                actual_days = day_count.dayCount(date, date + ql.Period(int(12 * p_pagos), ql.Months))
                
                factor_cobro = actual_days * (result_df.at[i, 'rate_tot']) / 365

            if tipo_de_cobro == 'por_periodo':
                tasa_en_periodo = periodicidad_tasa_number[periodicidad_tasa] * (
                    result_df.at[i, 'rate_tot'])
                factor_cobro = (1 + tasa_en_periodo) ** (
                        periodicidad_tasa_number[periodicidad_tasa] / self.number_to_user[self.periodicity]) - 1

            factor_cobro = factor_cobro / 100

            if i < self.grace_period_interest:
                result_df.at[i, 'interest'] = 0
            else:
                result_df.at[i, 'interest'] = factor_cobro * result_df.loc[i, 'beginning_balance']

            if i < self.grace_period_principal:
                result_df.at[i, 'ending_balance'] = result_df.loc[i, 'beginning_balance']
                if i == (len(dates) - 1):
                    pass
                else:
                    result_df.loc[i + 1, 'beginning_balance'] = result_df.at[i, 'ending_balance']
            else:
                result_df.at[i, 'ending_balance'] = result_df.loc[i, 'beginning_balance'] - (
                        self.original_balance / self.capital_payments)
                result_df.at[i, 'principal'] = self.original_balance / self.capital_payments
                if i == (len(dates) - 1):
                    pass
                else:
                    result_df.loc[i + 1, 'beginning_balance'] = result_df.at[i, 'ending_balance']

            result_df.at[i, 'payment'] = result_df.loc[i, 'interest'] + result_df.loc[i, 'principal']

        result_df.loc[:, 'date'] = result_df['date'].apply(ql_to_datetime)

        return result_df[index_rows].replace({np.nan: None})
