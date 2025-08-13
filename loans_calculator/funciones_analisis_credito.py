
import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
#sys.path.append("/Users/andre/Documents/xerenity/pysdk")
import numpy as np
import numpy_financial as npf

from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer
from utilities.date_functions import datetime_to_ql,ql_to_datetime, calculate_irr
import pandas as pd
import QuantLib as ql
from utilities.date_functions import days_30_360_ql,days_act_act_ql,days_act_365_ql

###### 


def calculate_days_from_value_date(df, value_date, start_date,convention):
    """
    Calculate the number of days between a value date and the previous and next payment dates using a specified day count convention.

    Parameters:
    - df (pd.DataFrame): DataFrame containing payment dates
    - value_date (pd.Timestamp): The value date to compare against
    - convention (str): Day count convention. One of '30/360', 'actual/actual', or 'actual/365'

    Returns:
    - dict: A dictionary with days between value_date and previous/next payment dates
    """
    # Ensure the 'date' column is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort the DataFrame by date
    df = df.sort_values(by='date')

    # Convert value_date to pandas datetime
    value_date = ql_to_datetime(value_date)
    
    # Find the previous and next payment dates
    prev_payment = df[df['date'] < value_date].sort_values(by='date', ascending=False).head(1)
    next_payment = df[df['date'] > value_date].sort_values(by='date').head(1)
    
    # Extract the dates
    prev_payment_date = prev_payment['date'].iloc[0] if not prev_payment.empty else start_date
    next_payment_date = next_payment['date'].iloc[0] if not next_payment.empty else None
    next_payment_interest = next_payment['interest'].iloc[0] if not next_payment.empty else None
    
    
    # Convert to QuantLib Dates
    value_date_ql = datetime_to_ql(value_date)
    prev_payment_date_ql = datetime_to_ql(prev_payment_date) if prev_payment_date is not None else None
    next_payment_date_ql = datetime_to_ql(next_payment_date) if next_payment_date is not None else None

    # Calculate days based on the specified convention
    if convention == '30/360':
        days_prev = days_30_360_ql(value_date_ql, prev_payment_date_ql) if prev_payment_date_ql else None
        days_next = days_30_360_ql(value_date_ql, next_payment_date_ql) if next_payment_date_ql else None
    elif convention == 'actual/actual':
        days_prev = days_act_act_ql(value_date_ql, prev_payment_date_ql) if prev_payment_date_ql else None
        days_next = days_act_act_ql(value_date_ql, next_payment_date_ql) if next_payment_date_ql else None
    elif convention == 'actual/365':
        days_prev = days_act_365_ql(value_date_ql, prev_payment_date_ql) if prev_payment_date_ql else None
        days_next = days_act_365_ql(value_date_ql, next_payment_date_ql) if next_payment_date_ql else None
    else:
        raise ValueError("Unsupported convention. Choose '30/360', 'actual/actual', or 'actual/365'.")
    try:
        accrued_interest = next_payment_interest * (-1 * days_prev) / (days_next - days_prev)
    except Exception as e:
        print(f"An error occurred: {e}")
        accrued_interest = 0

    return {
        'previous_payment_date': prev_payment_date,
        'days_to_previous': days_prev,
        'next_payment_date': next_payment_date,
        'days_to_next': days_next,
        'next_interest_payment': next_payment_interest,
        'accrued_interest': accrued_interest,
        'last_payment': df['date'].max()
    }

def create_cashflows_and_total_value(df, value_date,start_date,convention):
    """
    Create a DataFrame with only 'payment' and 'date' columns for payments after the value date,
    and calculate the total value of payments.

    Parameters:
    - df (pd.DataFrame): DataFrame containing payment dates and payment values
    - value_date (pd.Timestamp): The value date to filter against

    Returns:
    - cashflows (pd.DataFrame): DataFrame with 'payment' and 'date' columns
    - total_value (float): Sum of all payment values in the filtered DataFrame
    """

    # Ensure the 'date' column is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Convert value_date to pandas datetime
    value_date = ql_to_datetime(value_date)
    
    # Filter the DataFrame to include only rows with dates after the value date
    filtered_df = df[df['date'] > value_date]
    
    # Create the cashflows DataFrame with 'payment' and 'date' columns
    cashflows = filtered_df[['date', 'payment']].copy()
    
    info_dict=calculate_days_from_value_date(df, datetime_to_ql(value_date),start_date,convention)
    
    # Calculate the total value of payments
    total_value = filtered_df['principal'].sum()
    total_value=total_value+info_dict['accrued_interest']
    
    # Add the value_date and total_value as the first row
    total_row = pd.DataFrame({
        'date': [value_date],
        'payment': [-total_value]
    })
    # Concatenate the new row with the existing cashflows
    cashflows = pd.concat([total_row, cashflows], ignore_index=True)
    tenor=info_dict['last_payment']-value_date
   
    # List or dictionary to save errors
    errors = []

    result = {}
    try:
        irr = calculate_irr(cashflows['date'], cashflows['payment'], convention)
    except Exception as e:
        irr = 0
        errors.append(f"Error calculando irr: {str(e)}")
    result['irr'] = irr

    try:
        duration = calculate_debt_duration(filtered_df)
    except Exception as e:
        duration = 0
        errors.append(f"Error calculando duration: {str(e)}")
    result['duration'] = duration

    try:
        tenor = tenor.days / 365.25
    except Exception as e:
        tenor = 0
        errors.append(f"Error calculando tenor: {str(e)}")
    result['tenor'] = tenor

    try:
        interest = df['interest'].sum()
    except Exception as e:
        interest = 0
        errors.append(f"Error calculando interest: {str(e)}")
    result['interest'] = interest

    try:
        df_result = df
    except Exception as e:
        df_result = None
        errors.append(f"Error guardando df: {str(e)}")
    result['df'] = df_result

    try:
        total_value = total_value
    except Exception as e:
        total_value = 0
        errors.append(f"Error calculando total_value: {str(e)}")
    result['total_value'] = total_value

    try:
        principal_out_value = filtered_df['principal'].sum()
    except Exception as e:
        principal_out_value = 0
        errors.append(f"Error calculando principal_out_value: {str(e)}")
    result['principal_out_value'] = principal_out_value

    # Adding cashflows separately in case of errors
    try:
        result['cashflows'] = cashflows
    except Exception as e:
        result['cashflows'] = {}
        errors.append(f"Error guardando cashflows: {str(e)}")

    # Log or print errors if any occurred
    if errors:
        for error in errors:
            print(error)  # Or save this to a log file

     
    result.update(info_dict)
    return result

def calculate_debt_duration(df,rate=None):
    """
    Calculate the duration of debt from a dataframe with cash flow information.
    """
    # Ensure the 'date' column is in datetime format
    df['date'] = pd.to_datetime(df['date'])
    
    # Assuming the discount rate is the average of the rates for the duration calculation
    if rate is None:
        discount_rate = df['rate'].mean() / 100
    else:
        discount_rate=rate
    # Time periods (in years) from the start date
    df.loc[:, 't'] = (df['date'] - df['date'].iloc[0]).dt.days / 365.25

    # Present value of each cash flow (payment) discounted at the discount rate
    df.loc[:, 'PV'] = df['payment'] / (1 + discount_rate) ** df['t']

    # Time-weighted present value
    df.loc[:, 't_weighted_PV'] = df['t'] * df['PV']

    # Duration calculation: sum of time-weighted PV divided by sum of PV
    duration = df['t_weighted_PV'].sum() / df['PV'].sum()

    return duration


def merge_two_resulting_cashflows(loan0_df,loan1_df):
    # Merge the two dataframes on the 'date' column and sum the payments
    df_merged = pd.merge(loan0_df, loan1_df, on='date', how='outer', suffixes=('_cf1', '_cf2'))

    # Fill NaN values with 0 and sum the payments
    df_merged['total_payment'] = df_merged['payment_cf1'].fillna(0) + df_merged['payment_cf2'].fillna(0)


    # Assuming df_merged is the result of your previous merging operation
    df_result = df_merged[['date', 'total_payment']].copy()

    # Rename the 'total_payment' column to 'payment'
    df_result.rename(columns={'total_payment': 'payment'}, inplace=True)

    # Sort by date in ascending order
    df_result.sort_values(by='date', inplace=True)
    
    return df_result