# %%
import sys
sys.path.append("/Users/andre/Documents/xerenity/pysdk")
from utilities.date_functions import datetime_to_ql, ql_to_datetime
import QuantLib as ql
import pandas as pd
import datetime

class Loan:
    
    # Mapping from periodicity to its numerical value
    number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1 / 4, 'Bimensual': 1 / 6, 'Mensual': 1 / 12}
    

    # List of acceptable methods for counting days
    count_days_values = ['por_dias_360', 'por_dias_365', 'por_periodo']

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
                 db_info=None,
                 min_period_rate=None):
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
        user_to_spanish_periodo = {'Anual': 'SV',
                                'Semestral': 'SV', 
                                'Trimestral': 'TV',
                                'Bimensual': 'MV',
                                'Mensual': 'MV'}

        self.periodicity = periodicity
        self.periodicity_spanish=user_to_spanish_periodo[self.periodicity]
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
        self.min_period_rate=min_period_rate

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





    def generate_rates_ibr(self,
                            value_date,
                            curve):
            # Value date debe ser el dia actual, para que la curva IBR coincida con la valoracion
            # Curve deberia ser una curva de IBR generada con la valoracion de la curva actual 
            # Tipo de cobro depende del banco que emite el credito. 
            # Periodicidad tasa "SV", "TV"o "MV"
            grace_type=self.grace_type
            grace_period=self.grace_period
            periodicidad_tasa=self.periodicity_spanish
            # grace_type puede ser None o "capital" "interes" "ambos"
            # grace_period puede ser None o un numero entero
            
            tipo_de_cobro = self.days_count

            number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1 / 4, 'Bimensual': 1 / 6, 'Mensual': 1 / 12}
            periodicidad_tasa_number = {'SV': 0.5, 'TV': 1 / 4, 'MV': 1 / 12}

            periods = list(range(1, self.number_of_payments + 1))
            date_list = []

            start_date_ql = self.start_date_ql
            for i in range(len(periods)):
                date_list.append(
                    start_date_ql + ql.Period(int((i + 1) * (12 * number_to_user[self.periodicity])), ql.Months))
            # return dates
            dates = date_list
            tasas = pd.DataFrame(self.db_info[periodicidad_tasa])  # pd.DataFrame(get_last_n_banrep_ibr_1m_nom())
            # Convert 'fecha' column to datetime if it's not already in datetime format
            tasas['date'] = pd.to_datetime(tasas['fecha'])
            # Create a new DataFrame with 'your_date_list'
            result_data = {'date': dates}
            # Create an empty 'tasa' column in the result DataFrame
            result_data['rate'] = [None] * len(dates)
            result_df = pd.DataFrame(result_data)
            self.interest_rate=self.interest_rate*number_to_user[self.periodicity]*12
            self.min_period_rate=self.min_period_rate*number_to_user[self.periodicity]*12/100
            result_df['spread'] = self.interest_rate
            result_df['principal'] = 0 #self.original_balance / self.capital_payments


            # Iterate through each date in your_date_list
            moving_period = ql.Period(int(12 * number_to_user[self.periodicity]), ql.Months)
            result_df.at[0, 'beginning_balance'] = self.original_balance
            for i, date in enumerate(dates):
                # Find the closest date in the 'tasas' DataFrame
                if ql_to_datetime(date - moving_period) <= value_date:
                    closest_date = tasas['date'].sub(pd.Timestamp(ql_to_datetime(date - moving_period))).abs().idxmin()
                    # Assign the corresponding 'tasa' value to the result DataFrame
                    closest_value = tasas.at[closest_date, 'valor']
                    result_df.at[i, 'rate'] = closest_value
                    if self.min_period_rate==None:
                        result_df.at[i, 'rate_tot'] = result_df.at[i, 'rate'] + self.interest_rate
                    else:
                        result_df.at[i, 'rate_tot']=max(result_df.at[i, 'rate']+self.interest_rate,self.min_period_rate)
                # date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
                else:
                    
                    next_date = date + ql.Period(int(12 * periodicidad_tasa_number[periodicidad_tasa]), ql.Months)
                    result_df.at[i, 'rate'] = curve.forwardRate(date - moving_period, next_date - moving_period,
                                                                ql.Actual360(), ql.Simple).rate() * 100
                    if self.min_period_rate==None:
                        result_df.at[i, 'rate_tot'] = result_df.at[i, 'rate'] + self.interest_rate
                    else:
                        result_df.at[i, 'rate_tot']=max(result_df.at[i, 'rate']+self.interest_rate,self.min_period_rate)
                    

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
                    
                    factor_cobro = actual_days * (result_df.at[i, 'rate_tot'] + self.interest_rate) / 365

                    
                    
                
                if tipo_de_cobro == 'por_periodo':
                    tasa_en_periodo = periodicidad_tasa_number[periodicidad_tasa] * (
                        result_df.at[i, 'rate_tot'] + self.interest_rate)
                    factor_cobro = (1 + tasa_en_periodo) ** (
                        periodicidad_tasa_number[periodicidad_tasa] / self.number_to_user[self.periodicity]) - 1

                factor_cobro = factor_cobro / 100
              
                
                
                if i < self.grace_period_interest:
                    result_df.at[i, 'interest'] =0
                else:
                    result_df.at[i, 'interest'] = factor_cobro * result_df.loc[i, 'beginning_balance']

                if i < self.grace_period_principal:
                    result_df.at[i, 'ending_balance'] = result_df.loc[i, 'beginning_balance']
                    if i==(len(dates)-1):
                        print('xxxxxLastxxxxxx')
                    else:
                        result_df.loc[i+1, 'beginning_balance']=result_df.at[i, 'ending_balance']
                else:
                    result_df.at[i, 'ending_balance'] = result_df.loc[i, 'beginning_balance'] - (self.original_balance / self.capital_payments)
                    result_df.at[i, 'principal']=self.original_balance / self.capital_payments
                    if i==(len(dates)-1):
                        print('xxxxxLastxxxxxx')
                    else:
                        result_df.loc[i+1, 'beginning_balance']=result_df.at[i, 'ending_balance']

                result_df.at[i, 'payment'] = result_df.loc[i, 'interest'] + result_df.loc[i, 'principal']
                cf_table = result_df[['date', 'beginning_balance', 'rate', 'rate_tot', 'payment', 'interest', 'principal', 'ending_balance']]
                # pago_intereses
                #result_df = result_df.drop(result_df.index[-1])
                cf_table['date'] = cf_table['date'].apply(ql_to_datetime)
            
            return cf_table

    def generate_cash_flow_table_uvr(self, uvr=None):
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
        current_balance = self.original_balance

        for i in range(len(periods)):
            date_list.append(
                self.start_date_ql + ql.Period(int((i + 1) * (12 * self.number_to_user[self.periodicity])), ql.Months))
            interest_payment.append(
                current_balance * (self.interest_rate / 100 * self.number_to_user[self.periodicity]))
            principal_payment.append(monthly_payment - interest_payment[-1])
            ending_balance.append(current_balance - principal_payment[-1])

            current_balance = ending_balance[-1]

        # date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
        date_list = [ql_to_datetime(ql_date) for ql_date in date_list]
        cf_data = {
            'date': date_list,
            'interest': interest_payment,
            'rate': self.interest_rate,
            'principal': principal_payment,
            'payment': [monthly_payment] * len(periods),
            'ending_balance': ending_balance,
            'beginning_balance': [self.original_balance] + ending_balance[:-1]
        }

        cf_table = pd.DataFrame(data=cf_data, index=periods)
        cf_table = cf_table[['date', 'beginning_balance', 'rate', 'payment', 'interest', 'principal', 'ending_balance']]

        return cf_table




# %%
