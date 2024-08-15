import pandas as pd
import QuantLib as ql
from inflation_query.Inflation_query import InflacinImplicita
from server.main_server import XerenityFunctionServer, XerenityError, responseHttpOk
from utilities.date_functions import ql_to_datetime

class UVRPrintsServer(XerenityFunctionServer):

    def __init__(self, body):
        expected = {
            'calc_date': [int],
            'tes_table': [str],
            'inflation_lag_0': [str],
            'last_cpi': [str],
            'uvr': [str],
            'cbr': [str],
            'col_tes': [str]
        }

        body_fields = set(expected).difference(body.keys())

        if len(body_fields) > 0:
            raise XerenityError(message="Missing fields {}".format(str(body_fields)), code=400)

        self.calc_date = body['calc_date']
        self.uvr = body['uvr']
        self.cbr = body['cbr']
        self.tes_table = body['tes_table']
        self.inflation_lag_0 = body['inflation_lag_0']
        self.last_cpi = body['last_cpi']
        self.fixed_rate_excluded_bonds = ['tes_24', 'tesv_31']
        self.col_tes = body['col_tes']

    def calculate(self):
        cpi_call = InflacinImplicita(
            calc_date=ql.Date.todaysDate(),
            central_bank_rate=self.cbr,
            tes_table=pd.DataFrame(self.tes_table),
            inflation_lag_0=pd.DataFrame(self.inflation_lag_0),
            last_cpi=self.last_cpi,
            fixed_rate_excluded_bonds=self.fixed_rate_excluded_bonds,
            col_tes=self.col_tes,
            uvr=pd.DataFrame(self.uvr)
        )

        cpi = cpi_call.create_cpi_index()

        uvr_projec = cpi_call.calculo_serie_uvr(
            cpi_serie=cpi['total_cpi']
        )

        if 'fecha' in uvr_projec.columns:
            uvr_projec['fecha'] = pd.to_datetime(uvr_projec['fecha'])
            uvr_projec.set_index('fecha', inplace=True)

        # Ensure 'valor' column is of numeric type
        uvr_projec['valor'] = pd.to_numeric(uvr_projec['valor'], errors='coerce')

        # Drop rows with NaN values in 'valor'
        uvr_projec.dropna(subset=['valor'], inplace=True)

        # Convert index to datetime if it's not already
        if not isinstance(uvr_projec.index, pd.DatetimeIndex):
            uvr_projec.index = pd.to_datetime(uvr_projec.index)

        # Resample the DataFrame to daily frequency, filling in missing entries with NaN
        uvr_projec_daily = uvr_projec.resample('D').asfreq()

        # Use linear interpolation to fill in missing values
        uvr_projec_interpolated = uvr_projec_daily.interpolate(method='linear')

        # Filter out rows with dates less than today
        today = pd.Timestamp.today().normalize()  # normalize() to remove the time part
        uvr_projec_interpolated = uvr_projec_interpolated[uvr_projec_interpolated.index >= today]

        # Drop any rows with null values in the index (date) column
        uvr_projec_interpolated = uvr_projec_interpolated.dropna()
        uvr_projec_interpolated = uvr_projec_interpolated.reset_index().rename(columns={'index': 'fecha'})
        uvr_projec_interpolated['fecha'] = pd.to_datetime(uvr_projec_interpolated['fecha']).apply(str)

        if type(uvr_projec_interpolated) is pd.DataFrame:

            uvr_projec_interpolated['fecha'] = uvr_projec_interpolated['fecha'].apply(str)

            return responseHttpOk(body=uvr_projec_interpolated.to_dict(orient="records"))

        else:
            return responseHttpOk(body={"cash_flow": uvr_projec_interpolated.to_dict(orient='records')})

    def calculate_cpi_implicit(self):
        cpi_call = InflacinImplicita(
            calc_date=ql.Date.todaysDate(),
            central_bank_rate=self.cbr,
            tes_table=pd.DataFrame(self.tes_table),
            inflation_lag_0=pd.DataFrame(self.inflation_lag_0),
            last_cpi=self.last_cpi,
            fixed_rate_excluded_bonds=self.fixed_rate_excluded_bonds,
            col_tes=self.col_tes,
            uvr=pd.DataFrame(self.uvr)
        )

        cpi = cpi_call.create_cpi_index()

        cpi = cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})

        cpi['fecha'] = pd.to_datetime(cpi['fecha'])

        cpi['indice'] = cpi['indice'].pct_change(periods=12) * 100

        cpi.dropna(inplace=True)

        cpi_filtered = cpi[cpi['fecha'] >= ql_to_datetime(cpi_call.calc_date)]

        cpi_filtered.loc[:, 'fecha'] = cpi_filtered['fecha'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        if type(cpi_filtered) is pd.DataFrame:

            cpi_filtered.loc[:, 'fecha'] = cpi['fecha'].apply(str)

            return responseHttpOk(body=cpi_filtered.to_dict(orient="records"))

        else:
            return responseHttpOk(body={"cash_flow": cpi_filtered.to_dict(orient='records')})
