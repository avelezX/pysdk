import requests
import json
from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer

xty = Xerenity(
    username='s.salgado@saman-wm.com',
    password='simon_2006',
)

loan_data = xty.session.rpc('ibr_cash_flow_data',
                            {"credito_id":"54739020-ada0-4d68-bf74-f16eb8ecfd54","filter_date":"2025-09-23"}
                            ).execute().data

#print(loan_data)

response = requests.get('http://127.0.0.1:8000/ibr_rates',json=loan_data)
print(response.json())
# 'start_date': '2022-06-13T00:00:00'
# periodicity
#  number_of_payments
"""
all_loans_data = xty.session.rpc('uvr_cash_flow_data',
                                 {"credito_id":"79f83af8-6382-4c7f-ae0a-0a91668b37b9","filter_date":"2025-09-01"}
                                 ).execute().data

open("all_loan.json", "w+").write(json.dumps(all_loans_data))




print(response.json())

"""
