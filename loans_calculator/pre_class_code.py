import sys
sys.path.append("/Users/avelezxerenity/Documents/GitHub/pysdk")
#sys.path.append("/Users/andre/Documents/xerenity/pysdk")
import numpy as np
import numpy_financial as npf
from scipy.optimize import newton
import os
import json
from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer
from utilities.date_functions import datetime_to_ql,ql_to_datetime, calculate_irr
import pandas as pd
import QuantLib as ql
from loans_calculator.funciones_analisis_credito import merge_two_resulting_cashflows,create_cashflows_and_total_value,calculate_debt_duration
from  datetime import datetime
import pandas as pd
import json
from datetime import datetime



xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

all_loans_data = xty.get_all_loan_data(
    filter_date="2024-09-14"
)


# ibr_cashflow = xty.get_ibr_data(
#     loan_id="beb65020-e940-4995-9e1e-2f2208cdc638",
#     filter_date="2024-08-23"
# )
#calc = LoanCalculatorServer(ibr_cashflow, local_dev=True)
#loan_payments = calc.cash_flow_ibr()

days_converter_dir={'por_dias_360':'30/360','por_dias_365':'actual/365'}
db_info=all_loans_data['db_info']

# Define the value_date
value_date=datetime_to_ql(datetime.strptime(all_loans_data['filter_date'], '%Y-%m-%d'))
value_date_dt=ql_to_datetime(value_date)
db_info=all_loans_data['db_info']


# Initialize an empty dictionary to store results
results = {}

# Define a unique identifier for each loan (e.g., a code or index)
for i, loan in enumerate(all_loans_data['loans']):
    #try:
        # Create a copy of the current loan dictionary
        loan_temp = loan.copy()
        
        # Add or update 'db_info' in the copied dictionary
        loan_temp['db_info'] = db_info
        
        # Instantiate the LoanCalculatorServer with the updated dictionary
        calc = LoanCalculatorServer(loan_temp, local_dev=True)
        
        # Calculate loan payments
        loan_payments = calc.cash_flow_ibr()
        
        # Create cash flows and total value
        variables = create_cashflows_and_total_value(pd.DataFrame(loan_payments),
            value_date,
            datetime.strptime(loan['start_date'], '%Y-%m-%d'),
            days_converter_dir[loan['days_count']]
        )
        
                
        # Remove 'db_info' from loan_temp for the final result
        loan_temp.pop('db_info', None)  # Use pop to safely remove 'db_info' if it exists
        print(variables)
        # Store the variables along with the rest of the loan data
        results[f'loan_{i}'] = {
            'variables': variables,
            'loan_data': loan_temp
        }
        
    # except Exception as e:
    #     # Handle any unexpected exceptions
    #     print(f"An unexpected error occurred: {e}")
    #     print(loan)

# Print results to verify




# Initialize variables to store sums, counts, and loan IDs
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

# Dictionary to store information by bank
bank_data = {}

# Loop through each loan in the results dictionary
for loan_id, loan_info in results.items():
    # Extract the nested data from 'variables' and 'loan_data'
    total_value = loan_info['variables'].get('total_value')
    accrued_interest = loan_info['variables'].get('accrued_interest')
    irr = loan_info['variables'].get('irr')
    duration = loan_info['variables'].get('duration')
    tenor = loan_info['variables'].get('tenor')
    last_payment = loan_info['variables'].get('last_payment')  # Timestamp format
    start_date = loan_info['loan_data'].get('start_date')  # datetime format
    bank = loan_info['loan_data'].get('bank')
    loan_type = loan_info['loan_data'].get('type')  # Loan type: 'fija' or 'ibr'
    loan_id = loan_info['loan_data'].get('id')  # Loan ID
    
    # Append the loan ID to the list
    loan_ids_list.append(loan_id)
    
    # Initialize bank data structure if it does not exist
    if bank not in bank_data:
        bank_data[bank] = {
            'total_value': 0, 
            'weighted_irr_sum': 0, 
            'accrued_interest': 0,
            'weighted_duration_sum': 0,
            'weighted_tenor_sum': 0,
            'loan_count': 0,  # Initialize loan count for the bank
            'outdated_loan_count': 0,  # Initialize outdated loan count for the bank
            'total_value_fija': 0,  # Initialize total value for 'fija' loans
            'weighted_irr_fija_sum': 0,  # Initialize weighted IRR sum for 'fija'
            'total_value_ibr': 0,  # Initialize total value for 'ibr' loans
            'weighted_irr_ibr_sum': 0,  # Initialize weighted IRR sum for 'ibr'
            'loan_ids': []  # Initialize list to store loan IDs for the bank
        }
    
    # Check if any critical values are missing
    if pd.isna(total_value) or pd.isna(accrued_interest) or pd.isna(irr) or pd.isna(duration) or pd.isna(tenor):
        print(f"Warning: Missing data detected in loan {loan_id}:")
        print(f"total_value={total_value}, accrued_interest={accrued_interest}, irr={irr}, duration={duration}, tenor={tenor}, bank={bank}")
        
        # Increment the count of loans with missing data
        not_calculated_loan_count += 1
        continue  # Skip this loan from further calculations
    
    # Check if the loan is outdated: value_date_dt must be between start_date and last_payment
    if not (start_date < value_date_dt < last_payment):
        outdated_loan_count += 1
        continue  # Skip outdated loans from calculations
    
    # Add to total sums for all loans
    total_value_sum += total_value
    accrued_interest_sum += accrued_interest
    total_loan_count += 1  # Increment the total loan count
    
    # Update bank-specific data
    bank_data[bank]['total_value'] += total_value
    bank_data[bank]['weighted_irr_sum'] += irr * total_value
    bank_data[bank]['accrued_interest'] += accrued_interest
    bank_data[bank]['weighted_duration_sum'] += duration * total_value
    bank_data[bank]['weighted_tenor_sum'] += tenor * total_value
    bank_data[bank]['loan_count'] += 1  # Increment the loan count for the bank
    
    # Update total_value and weighted IRR by loan type
    if loan_type == 'fija':
        bank_data[bank]['total_value_fija'] += total_value
        bank_data[bank]['weighted_irr_fija_sum'] += irr * total_value
    elif loan_type == 'ibr':
        bank_data[bank]['total_value_ibr'] += total_value
        bank_data[bank]['weighted_irr_ibr_sum'] += irr * total_value

    # Append the loan ID to the bank's list of loan IDs
    bank_data[bank]['loan_ids'].append(loan_id)

# Calculate weighted averages for each bank
for bank, data in bank_data.items():
    data['average_irr'] = data['weighted_irr_sum'] / data['total_value'] if data['total_value'] > 0 else None
    data['average_duration'] = data['weighted_duration_sum'] / data['total_value'] if data['total_value'] > 0 else None
    data['average_tenor'] = data['weighted_tenor_sum'] / data['total_value'] if data['total_value'] > 0 else None
    
    # Calculate weighted average IRRs for 'fija' and 'ibr' loans
    data['average_irr_fija'] = (data['weighted_irr_fija_sum'] / data['total_value_fija']
                                if data['total_value_fija'] > 0 else None)
    data['average_irr_ibr'] = (data['weighted_irr_ibr_sum'] / data['total_value_ibr']
                               if data['total_value_ibr'] > 0 else None)

    # Convert the list of loan IDs to JSON format
    data['loan_ids'] = json.dumps(data['loan_ids'])

# Convert the bank data into a DataFrame
bank_df = pd.DataFrame.from_dict(bank_data, orient='index')

# Calculate totals for the summary row
total_value_fija_sum = bank_df['total_value_fija'].sum()
total_value_ibr_sum = bank_df['total_value_ibr'].sum()
weighted_irr_fija_sum = bank_df['weighted_irr_fija_sum'].sum()
weighted_irr_ibr_sum = bank_df['weighted_irr_ibr_sum'].sum()

# Calculate total weighted sums
total_weighted_irr_sum = bank_df['weighted_irr_sum'].sum()
total_weighted_duration_sum = bank_df['weighted_duration_sum'].sum()
total_weighted_tenor_sum = bank_df['weighted_tenor_sum'].sum()

# Calculate weighted averages
total_average_irr = (total_weighted_irr_sum / total_value_sum) if total_value_sum > 0 else None
total_average_duration = (total_weighted_duration_sum / total_value_sum) if total_value_sum > 0 else None
total_average_tenor = (total_weighted_tenor_sum / total_value_sum) if total_value_sum > 0 else None
total_average_irr_fija = (weighted_irr_fija_sum / total_value_fija_sum) if total_value_fija_sum > 0 else None
total_average_irr_ibr = (weighted_irr_ibr_sum / total_value_ibr_sum) if total_value_ibr_sum > 0 else None

# Add the total sums as a separate DataFrame row
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

# Combine the total row and bank-specific data
final_df = pd.concat([bank_df, totals])

# Reorder the columns to include the new 'loan_ids' field
final_df = final_df[['total_value', 'accrued_interest', 'average_irr', 'average_duration', 'average_tenor', 'loan_count', 
                     'outdated_loan_count', 'total_value_fija', 'average_irr_fija', 'total_value_ibr', 'average_irr_ibr',
                     'not_calculated_loan_count', 'loan_ids']]

# Sort the DataFrame by total_value in descending order
final_df = final_df.sort_values(by='total_value', ascending=False)