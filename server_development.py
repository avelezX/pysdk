import os
import json
from src.xerenity.xty import Xerenity
from server.loan_calculator.loan_calculator import LoanCalculatorServer

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

ibr_cashflow = xty.get_ibr_data(
    loan_id="c5f0df1a-b69e-4367-9802-d665afcb844b",
    filter_date="2024-08-23"
)

open("ibr_cashflow.json", "w+").write(json.dumps(ibr_cashflow))

calc = LoanCalculatorServer(ibr_cashflow, local_dev=True)
loan_payments = calc.cash_flow_ibr()

open("loan_payments.json", "w+").write(json.dumps(loan_payments))
