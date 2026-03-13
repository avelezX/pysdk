from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from implicitas.Implicitas import Implicitas
from loan.helperFunctions import QlHelperFunctions
from datetime import datetime
import pandas as pd
import QuantLib as ql
from utilities.date_functions import ql_to_datetime


class IbQuotesServer(XerenityFunctionServer):

    def __init__(self, body):

        expected = {
            'interval_tenor': [int],
            'start_date': [str]
        }

        body_fields = set(expected).difference(body.keys())

        if len(body_fields) > 0:
            raise XerenityError(message="Missing fields {}".format(str(body_fields)), code=400)

        for key, val in expected.items():
            if not type(body[key]) in val:
                raise XerenityError(message="{} must be {}".format(key, 400), code=400)

        if body['interval_tenor'] not in [1, 3, 6, 12]:
            raise XerenityError(message="interval_tenor must be 1,3,6,12", code=400)

        self.quotes_cal: Implicitas = Implicitas(**body)

    def calculate(self):

        """
        try:

        except Exception as er:
            raise XerenityError(message=str(er), code=400)
        """

        qlHelper = QlHelperFunctions()

        value_date = datetime.strptime(self.quotes_cal.start_date, '%Y-%m-%dT%H:%M:%S')

        curve = qlHelper.create_curve(
            db_info=self.quotes_cal.ibr_quotes,
            value_date=value_date,
            years=20
        )

        fwd_curve = self.quotes_cal.rates_generation(curve=curve, start_date=value_date, interval_period='m')

        fwd_curve = fwd_curve.reset_index().rename(columns={'Maturity Date': 'fecha'})
        fwd_curve['fecha'] = pd.to_datetime(fwd_curve['fecha']).apply(str)
        fwd_curve['rate'] = fwd_curve['rate'] * 100

        if type(fwd_curve) is pd.DataFrame:

            fwd_curve['fecha'] = fwd_curve['fecha'].apply(str)

            return responseHttpOk(body=fwd_curve.to_dict(orient="records"))

        else:
            return responseHttpOk(body={"cash_flow": str(fwd_curve)})
