import json

from loans_calculator.loan_structure import Loan
from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from datetime import datetime
import pandas as pd
import QuantLib as ql
from swap_functions.main import full_ibr_curve_creation
from utilities.colombia_calendar import calendar_colombia


class LoanCalculatorServer(XerenityFunctionServer):

    def __init__(self, body):

        self.body = body

        expected = {
            'interest_rate': [int, float],
            'periodicity': [str],
            'number_of_payments': [float, int],
            'start_date': [str],
            'original_balance': [float, int]
        }

        body_fields = set(expected).difference(body.keys())

        if len(body_fields) > 0:
            raise XerenityError(message="Missing fields {}".format(str(body_fields)), code=400)

        for key, val in expected.items():
            if not type(body[key]) in val:
                raise XerenityError(message="{} must be {}".format(key, 400), code=400)

        if not self.body['periodicity'] in Loan.number_to_user.keys():
            raise XerenityError(message="Periodicity must be {}".format(",".join(Loan.number_to_user.keys())), code=400)

        try:
            # 2024-01-01
            self.body['start_date'] = datetime.strptime(body['start_date'], '%Y-%m-%d')

        except Exception as e:

            raise XerenityError(message=str(e), code=400)

        self.loan = Loan(**self.body)

    def period_payment(self):

        try:

            payment = self.loan.calculate_custom_period_payment()

            return responseHttpOk(body={"payment": str(payment)})

        except Exception as er:
            raise XerenityError(message=str(er), code=400)

    def cash_flow(self):

        try:

            payment = self.loan.generate_cash_flow_table()

            if type(payment) is pd.DataFrame:

                payment['date'] = payment['date'].apply(str)

                return responseHttpOk(body=payment.to_dict(orient="records"))

            else:
                return responseHttpOk(body={"cash_flow": str(payment)})

        except Exception as er:

            raise XerenityError(message=str(er), code=400)

    def cash_flow_ibr(self):
        """

        Function to calculate cashflow with ibr data
        :return:
        """
        try:

            self.loan.rate_type = 'IBR'
            today = datetime.today().date()
            start = ql.Date(today.day, today.month, today.year)
            ql_today = ql.Date(today.day, today.month, today.year)
            calendar = calendar_colombia()
            depth_search = 8

            while not calendar.isBusinessDay(start) and depth_search >= 0:
                start = calendar.advance(start, -1, ql.Days)
                depth_search = depth_search - 1

            if depth_search == 0:
                print("No business day found in {} days".format(depth_search))
                start = ql_today

            value_date = datetime(year=start.year(), month=start.month(), day=start.dayOfMonth())

            curve_details = full_ibr_curve_creation(
                desired_date_valuation=value_date,
                calendar=calendar_colombia(),
                day_to_avoid_fwd_ois=7,
                db_info=self.loan.db_info
            )

            curve = curve_details.crear_curva(days_to_on=1)

            payment = self.loan.generate_rates_ibr(
                value_date=value_date,
                curve=curve,
                tipo_de_cobro='por_dias_360',
                periodicidad_tasa='MV'
            )

            if type(payment) is pd.DataFrame:

                payment['date'] = payment['date'].apply(str)

                return responseHttpOk(body=payment.to_dict(orient="records"))

            else:
                return responseHttpOk(body={"cash_flow": str(payment)})

        except Exception as er:

            raise XerenityError(message=str(er), code=400)
