import json
import os
from src.xerenity.xty import Xerenity

xty = Xerenity(
    username=os.getenv('XTY_USER'),
    password=os.getenv('XTY_PWD'),
)

all_loans_data = xty.get_all_loan_data(
    filter_date="2024-09-14"
)

open("all_loan.json", "w+").write(json.dumps(all_loans_data))
