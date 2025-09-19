from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from datetime import datetime
import pandas as pd

from loan.Loan import Loan
from loan.ibrLoan import IbrLoan
from loan.fixedRateLoan import FixedRateLoan


class LoanCalculatorServer(XerenityFunctionServer):

    def __init__(self, body, local_dev=False):

        self.body = body

        self.local_dev = local_dev

        expected = {
            'interest_rate': [int, float],
            'periodicity': [str],
            'number_of_payments': [float, int],
            'start_date': [str],
            'original_balance': [float, int],
            'bank': [str, None],
            'id': [str],
            'type': [str],
            'owner': [str]
        }

        body_fields = set(expected).difference(body.keys())

        if len(body_fields) > 0:
            raise XerenityError(message="Missing fields {}".format(str(body_fields)), code=400)

        for key, val in expected.items():
            if not type(body[key]) in val:
                raise XerenityError(message="{} must be {}".format(key, 400), code=400)

        if not self.body['periodicity'] in Loan.number_to_user.keys():
            raise XerenityError(
                message="Periodicity must be {}".format(",".join(Loan.number_to_user.keys())), code=400)

        if 'days_count' in self.body:
            if self.body['days_count'] not in Loan.count_days_values and self.body['days_count'] != None:
                raise XerenityError(
                    message="Conteo de día debe ser uno de los siguientes {}".format(
                        ",".join(Loan.count_days_values)),
                    code=400
                )
        try:
            # 2024-01-01
            self.body['start_date'] = datetime.strptime(body['start_date'], '%Y-%m-%d')

        except Exception as e:

            raise XerenityError(message=str(e), code=400)

        # self.loan = Loan(**self.body)

    def period_payment(self):

        try:
            loan = FixedRateLoan(**self.body)
            payment = loan.generate_cash_flow()

            return responseHttpOk(body={"payment": str(payment)})

        except Exception as er:
            raise XerenityError(message=str(er), code=400)

    def cash_flow(self):

        try:

            loan = FixedRateLoan(**self.body)
            payment = loan.generate_cash_flow(uvr=False)

            if type(payment) is pd.DataFrame:

                payment['date'] = payment['date'].apply(str)

                if self.local_dev:
                    return payment.to_dict(orient="records")
                else:
                    return responseHttpOk(body=payment.to_dict(orient="records"))

            else:
                if self.local_dev:
                    return {"cash_flow": str(payment)}
                else:
                    return responseHttpOk(body={"cash_flow": str(payment)})

        except Exception as er:

            raise XerenityError(message=str(er), code=400)

    def cash_flow_ibr(self):
        """

        Function to calculate cashflow with ibr data
        :return:
        """

        loan = IbrLoan(**self.body)

        loan.rate_type = 'IBR'

        value_date_db = loan.db_info['fecha'][0]

        value_date = datetime.strptime(value_date_db, '%Y-%m-%dT%H:%M:%S')

        payment = loan.generate_cash_flow(
            value_date=value_date
        )

        if type(payment) is pd.DataFrame:

            payment['date'] = payment['date'].apply(str)

            if self.local_dev:
                return payment.to_dict(orient="records")
            else:
                return responseHttpOk(body=payment.to_dict(orient="records"))

        else:
            if self.local_dev:
                return {"cash_flow": str(payment)}
            else:
                return responseHttpOk(body={"cash_flow": str(payment)})
        #try:


        #except Exception as er:
        #    raise XerenityError(message=str(er), code=400)

    def cash_flow_uvr(self):
        """
        Escribir como calcular el credito de un UV
        """
        try:
            loan = FixedRateLoan(**self.body)
            payment = loan.generate_cash_flow(uvr=True)

            if type(payment) is pd.DataFrame:

                payment['date'] = payment['date'].apply(str)

                if self.local_dev:
                    return payment.to_dict(orient="records")
                return responseHttpOk(body=payment.to_dict(orient="records"))
            else:
                if self.local_dev:
                    return {"cash_flow": str(payment)}

                return responseHttpOk(body={"cash_flow": str(payment)})
        except Exception as er:

            raise XerenityError(message=str(er), code=400)
