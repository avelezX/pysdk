import os
import json
from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

all_loans_data = xty.get_all_loan_data(
    filter_date="2024-08-23"
)

open("all_loan.json", "w+").write(json.dumps(all_loans_data))

#calc = LoanCalculatorServer(ibr_cashflow, local_dev=True)
#loan_payments = calc.cash_flow_ibr()

#open("loan_payments.json", "w+").write(json.dumps(loan_payments))
