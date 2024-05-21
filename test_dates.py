import json

from loans_calculator.loan_structure import Loan
from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from datetime import datetime
import pandas as pd
import QuantLib as ql
from swap_functions.main import full_ibr_curve_creation
from utilities.colombia_calendar import calendar_colombia

today = datetime.today().date()
start = ql.Date(today.day, today.month, today.year)

print("--------TODAY-------")
print(start)

calendar = calendar_colombia()
start = calendar.advance(start, -2, ql.Days)
print("--------YESTERDAY-------")
print(start)

while not calendar.isBusinessDay(start):
    start = calendar.advance(start, -1, ql.Days)

print("--------BUSINESS DAY-------")
print(start)

print(start.month())

value_date = datetime(year=start.year(), month=start.month(), day=start.dayOfMonth())

print(value_date)
