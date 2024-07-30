from datetime import datetime
import pandas as pd
import QuantLib as ql
from utilities.date_functions import datetime_to_ql
from bond_functions.tes_quant_lib_details import tes_quantlib_det
from bond_functions.bond_structure import tes_bond_structure



class BondCurve:
    """
    A class for managing bond curves and performing curve fitting.

    Attributes:
        currency (str): Currency of the bond curve.
        country (str): Country of the bond curve.
        supabase: Supabase instance.
        bond_info_df (pd.DataFrame): DataFrame containing bond information.

    Methods:
        create_ql_db_dict: Create a dictionary of QuantLib bond structures.
        create_df: Create a DataFrame with bond trading data.
        ns_param: Perform curve fitting and return a function for optimization.
    """

    def __init__(self, currency=None, country=None, bond_info_df=None, bond_ql_details=tes_quantlib_det):
        """
        Initialize the BondCurve instance.

        Args:
            currency (str): Currency of the bond curve.
            country (str): Country of the bond curve.
            supabase: Supabase instance.
            bond_info_df (pd.DataFrame): DataFrame containing bond information.
        """
        self.currency = currency
        self.country = country
        self.bond_ql_details = bond_ql_details

        self.bond_info_df = bond_info_df.set_index('name')
        self.bond_dict_cop = {}

    def create_ql_db_dict(self):
        """
        Create a dictionary of QuantLib bond structures.

        Returns:
            dict: Dictionary of bond structures.
        """
        self.bond_info_df['emision'] = pd.to_datetime(self.bond_info_df['emision'])
        self.bond_info_df['maduracion'] = pd.to_datetime(self.bond_info_df['maduracion'])

        for index, row in self.bond_info_df.iterrows():
            bond = tes_bond_structure(row['emision'], row['maduracion'], row['cupon'], index)
            if row['moneda'] == self.currency:
                self.bond_dict_cop[index] = bond
        return self.bond_dict_cop

    def create_df(self, colt_tes, excluded_bonds=[]):
        """
        Create a DataFrame with bond trading data.

        Args:
            excluded_bonds (list): List of bonds to be excluded from the DataFrame.

        Returns:
            pd.DataFrame: DataFrame with bond trading data.
        """
        cop_df = pd.DataFrame()
        bond_dict_cop = self.create_ql_db_dict()

        for key, value in bond_dict_cop.items():
            if key in excluded_bonds:
                pass
            else:
                value_df = self.search_tes_by_name(col_tes=colt_tes, name=value.name)
                cop_df.loc[key, 'volume'] = value_df['volume']
                cop_df.loc[key, 'day'] = datetime.strptime(
                    value_df['operation_time'].split('T')[0], '%Y-%m-%d').timestamp()
                cop_df.loc[key, 'close'] = value_df['close']
                cop_df.loc[key, 'open'] = value_df['open']
                cop_df.loc[key, 'high'] = value_df['high']
                cop_df.loc[key, 'low'] = value_df['low']
                cop_df.loc[key, 'maturity'] = pd.to_datetime(value.maturity).date()
        return cop_df.sort_values(by='maturity')

    def search_tes_by_name(self, col_tes, name):

        for t in col_tes:
            if t['tes'] == name:
                return t
        return None

    def create_bond_helpers(self, cop_df=None, excluded_bonds=[]):
        if cop_df is None:
            cop_df = self.create_df(excluded_bonds=excluded_bonds)

        bond_helpers = []
        bond_rates = cop_df['close'] / 100
        cop_df['ql_date_column'] = cop_df['maturity'].apply(datetime_to_ql)
        bond_maturities = cop_df['ql_date_column']

        for r, m in zip(bond_rates, bond_maturities):
            termination_date = m
            schedule = ql.Schedule(self.bond_ql_details['calc_date'],
                                   termination_date,
                                   self.bond_ql_details['coupon_frequency'],
                                   self.bond_ql_details['calendar'],
                                   self.bond_ql_details['bussiness_convention'],
                                   self.bond_ql_details['bussiness_convention'],
                                   ql.DateGeneration.Backward,
                                   self.bond_ql_details['end_of_month'])

            helper = ql.FixedRateBondHelper(ql.QuoteHandle(ql.SimpleQuote(self.bond_ql_details['face_amount'])),
                                            self.bond_ql_details['settlement_days'],
                                            self.bond_ql_details['face_amount'],
                                            schedule,
                                            [r],
                                            self.bond_ql_details['day_count'],
                                            self.bond_ql_details['bussiness_convention'],
                                            )
            bond_helpers.append(helper)
        return bond_helpers

    def yield_curve_ql(self, calc_date, bond_helpers=None, depo_helper=None):
        if bond_helpers is None:
            bond_helpers = self.create_bond_helper()

        if depo_helper is None:
            rate_helpers = bond_helpers
        else:
            rate_helpers = depo_helper + bond_helpers

        yieldcurve = ql.PiecewiseLogCubicDiscount(calc_date,
                                                  rate_helpers,
                                                  self.bond_ql_details['day_count'])
        return yieldcurve

    # def ns_param(self, cop_df=None, excluded_bonds=[], start_date=pd.Timestamp.now().date()):
    #     """
    #     Perform curve fitting and return a function for optimization.

    #     Args:
    #         cop_df (pd.DataFrame): DataFrame with bond trading data.
    #         excluded_bonds (list): List of bonds to be excluded from the fit.
    #         start_date (datetime.date): Start date for curve fitting.

    #     Returns:
    #         function: Function for optimization.
    #     """
    #     if cop_df is None:
    #         cop_df = self.create_df(excluded_bonds)

    #     def nelson_siegel(x, beta0, beta1, beta2, tau):
    #         return beta0 + beta1 * ((1 - np.exp(-x / tau)) / (x / tau)) + beta2 * (((1 - np.exp(-x / tau)) / (x / tau)) - np.exp(-x / tau))

    #     def ns_curve_param(x, y, initial_guess=[1, 1, 1, 1]):
    #         params, covariance = curve_fit(nelson_siegel, x, y, p0=initial_guess)
    #         return params

    #     start_date = datetime.combine(start_date, datetime.min.time())
    #     x_values = (pd.to_datetime(cop_df['maturity']) - start_date).dt.days.values
    #     y_values = cop_df['close']
    #     params = ns_curve_param(x_values, y_values, initial_guess=[1, 1, 1, 1])

    #     def nel_sig_opt(x_to_est):
    #         return nelson_siegel(x_to_est, *params)
