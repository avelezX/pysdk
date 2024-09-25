import pandas as pd
from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from loans_calculator.portfolio_summary_function import LoanPortfolioAnalyzer


class AllLoanServer(XerenityFunctionServer):
    def __init__(self, body):
        expected = {
            'filter_date': [str]
        }

        body_fields = set(expected).difference(body.keys())

        if len(body_fields) > 0:
            raise XerenityError(message="Missing fields {}".format(str(body_fields)), code=400)

        self.all_loan_data = body

        self.filter_date = body['filter_date']

    def calculate(self):
        analyzer = LoanPortfolioAnalyzer(all_loan_data=self.all_loan_data, filter_date=self.filter_date)
        analyzer.retrieve_data()
        analyzer.process_loans()
        analyzer.aggregate_data()
        analyzer.calculate_weighted_averages()
        final_df = analyzer.get_final_dataframe()

        if type(final_df) is pd.DataFrame:

            return responseHttpOk(body=final_df.to_dict(orient="records"))

        else:
            return responseHttpOk(body={"cash_flow": str(final_df)})
