# %%
import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
from datetime import datetime
from utilities.date_functions import datetime_to_ql,ql_to_datetime
import pandas as pd
import QuantLib as ql
import pandas as pd
from datetime import datetime
import numpy_financial as npf
import pandas as pd


class Loan:
    def __init__(self,interest_rate, periodicity,number_of_payments,start_date,original_balance,rate_type='fixed',db_info=None):
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

        self.periodicity= periodicity
        self.number_of_payments=number_of_payments
        self.interest_rate = interest_rate
        self.original_balance = original_balance
        self.start_date = start_date
        self.start_date_ql = datetime_to_ql(self.start_date)
        self.rate_type=rate_type
        self.db_info=db_info
      
        

        self.number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1/4, 'Bimensual': 1/6, 'Mensual': 1/12}


    # def calculate_monthly_payment(self):
    #     """
    #     Calculates the monthly payment for the loan.

    #     Returns:
    #     - float: The calculated monthly payment.
    #     """
    #     monthly_interest_rate = self.interest_rate / 12 / 100
    #     num_payments = self.term_months
    #     monthly_payment = npf.pmt(monthly_interest_rate, num_payments, -self.original_balance)
    #     return monthly_payment
    

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
        periodic_interest_rate = annual_interest_rate / (1/self.number_to_user[self.periodicity])
        discount_factor = ((1 + periodic_interest_rate) ** self.number_of_payments - 1) / (periodic_interest_rate * (1 + periodic_interest_rate) ** self.number_of_payments)
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
        date_list=[]
        current_balance = self.original_balance

        

        for i in range(len(periods)):
            date_list.append(self.start_date_ql + ql.Period(int((i+1)*(12*self.number_to_user[self.periodicity])), ql.Months))
            interest_payment.append(current_balance * (self.interest_rate / 100 *self.number_to_user[self.periodicity]))
            principal_payment.append(monthly_payment - interest_payment[-1])
            ending_balance.append(current_balance - principal_payment[-1])
            
            current_balance = ending_balance[-1]

        #date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
        date_list = [ql_to_datetime(ql_date) for ql_date in date_list]
        cf_data = {
            'date': date_list,
            'interest': interest_payment,
            'rate':self.interest_rate,
            'principal': principal_payment,
            'payment': [monthly_payment] * len(periods),
            'ending_balance': ending_balance,
            'beginning_balance': [self.original_balance] + ending_balance[:-1]
        }

        cf_table = pd.DataFrame(data=cf_data, index=periods)
        cf_table = cf_table[['date', 'beginning_balance','rate','payment', 'interest', 'principal', 'ending_balance']]

        return cf_table
    
    def generate_rates_ibr(self,value_date,curve,tipo_de_cobro='por_dias_360',periodicidad_tasa='MV'):
        
        number_to_user = {'Anual': 1, 'Semestral': 0.5, 'Trimestral': 1/4, 'Bimensual': 1/6, 'Mensual': 1/12}
        periodicidad_tasa_number = { 'SV': 0.5, 'TV': 1/4, 'MV': 1/12}
        
        periods = list(range(1, self.number_of_payments + 1))
        date_list=[]
        
        start_date_ql = self.start_date_ql
        for i in range(len(periods)):
            date_list.append(start_date_ql + ql.Period(int((i+1)*(12*number_to_user[self.periodicity])), ql.Months))
        #return dates
        dates=date_list
        tasas=pd.DataFrame(self.db_info[periodicidad_tasa]) #pd.DataFrame(get_last_n_banrep_ibr_1m_nom())
        # Convert 'fecha' column to datetime if it's not already in datetime format
        tasas['date'] = pd.to_datetime(tasas['fecha'])
        # Create a new DataFrame with 'your_date_list'
        result_data = {'date': dates}
        # Create an empty 'tasa' column in the result DataFrame
        result_data['rate'] = [None] * len(dates)
        result_df = pd.DataFrame(result_data)
        result_df['spread']=self.interest_rate
        result_df['principal']=self.original_balance/self.number_of_payments
        #Iterate through each date in your_date_list
        moving_period=ql.Period(int(12*number_to_user[self.periodicity]), ql.Months)
                
        for i, date in enumerate(dates):
            # Find the closest date in the 'tasas' DataFrame
            if ql_to_datetime(date-moving_period) < value_date:
                closest_date = tasas['date'].sub(pd.Timestamp(ql_to_datetime(date-moving_period))).abs().idxmin()
            # Assign the corresponding 'tasa' value to the result DataFrame
                closest_value = tasas.at[closest_date, 'valor']
                result_df.at[i, 'rate'] = closest_value
            #date_list = [self.start_date_ql + ql.Period(i, ql.Months) for i in range(len(periods))]
            else:
                
                next_date=date+ ql.Period(int(12*periodicidad_tasa_number[periodicidad_tasa]), ql.Months)
                result_df.at[i,'rate']=curve.forwardRate(date-moving_period, next_date-moving_period, ql.Actual360(), ql.Simple).rate()*100

            if tipo_de_cobro=='por_dias_360':
                # Calculate the actual number of days between the two dates
                # Usamos la periodicidad en pagos.
                p_pagos=self.number_to_user[self.periodicity]
                day_count = ql.ActualActual(ql.ActualActual.ISDA)
                actual_days = day_count.dayCount(date, date+ ql.Period(int(12*p_pagos), ql.Months))
                factor_cobro=actual_days*(result_df.at[i,'rate']+self.interest_rate)/360
                
            if tipo_de_cobro=='por_dias_365':
                # Calculate the actual number of days between the two dates
                # Usamos la periodicidad en pagos.
                p_pagos=self.number_to_user[self.periodicity]
                day_count = ql.ActualActual(ql.ActualActual.ISDA)
                actual_days = day_count.dayCount(date, date+ ql.Period(int(12*p_pagos), ql.Months))
                factor_cobro=actual_days*(result_df.at[i,'rate']+self.interest_rate)/365
            if tipo_de_cobro=='por_periodo':
                tasa_en_periodo=periodicidad_tasa_number[periodicidad_tasa]*(result_df.at[i,'rate']+self.interest_rate)
                factor_cobro=(1+tasa_en_periodo)**(periodicidad_tasa_number[periodicidad_tasa]/self.number_to_user[self.periodicity])-1
            
            
            #result_df.at[i,'factor_cobro']=factor_cobro
            result_df.at[i,'beginning_balance']=self.original_balance-(self.original_balance/self.number_of_payments)*i
            result_df.at[i,'interest']=factor_cobro*result_df.at[i,'beginning_balance']
            result_df.at[i,'ending_balance']=self.original_balance-(self.original_balance/self.number_of_payments)*(i+1)
            result_df.at[i,'payment']=result_df.at[i,'interest']+result_df.at[i,'principal']
            cf_table = result_df[['date','beginning_balance','rate','payment', 'interest', 'principal', 'ending_balance']]
            #pago_intereses
             

        return cf_table
        



# %%
