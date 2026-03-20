import json
import sys

# sys.path.insert(0,'/Users/avelezxerenity/.pyenv/versions/xerenity/lib/python3.10/site-packages')
sys.path.append('/Users/avelezxerenity/Documents/GitHub/xerenity-dm')

from urllib.parse import urlencode
import QuantLib as ql
import requests
from io import StringIO
import pandas as pd
from functions_DM.utility_func import columns_with_date
from data_collectors.dtcc.dtcc_collector import DttcColelctor
import numpy as np
import datetime

query_date = ql.Date.todaysDate()


class IBRSwapCollector(DttcColelctor):
    def __init__(self):
        super().__init__(name='dtcc_ibr')

        self.has_intra_day_prices = True

        # self.api_key = '0ecb1545aa91670f6b492c475b020601'

        # Variables del collector global de DTCC 
        # self.fred_url = 'https://pddata.dtcc.com/gtr/dailySearchCsv.do'
        self.fred_url = 'https://pddata.dtcc.com/ppd/api/search/webdisplay'
        #
        self.headers = {'Content-Type': 'application/json'}
        # Variables del collector y busqueda specifica de IBR swaps.
        self.product_name = ['COP-IBR-OIS-COMPOUND', 'COP-IBR-OIS Compound']
        self.columns = [
                        # --- core identifiers & timestamps ---
                        "disseminationIdentifier", "originalDisseminationIdentifier", "actionType",
                        "eventTimestamp", "productName",
                        "executionTimestamp", "effectiveDate", "expirationDate",
                        # --- notional & currency ---
                        "notionalAmountLeg1", "notionalAmountLeg2",
                        "notionalCurrencyLeg1", "notionalCurrencyLeg2",
                        # --- rates & underliers ---
                        "fixedRateLeg1", "fixedRateLeg2",
                        "underlierIDLeg1", "underlierIDLeg2",
                        "floatingRateResetFrequencyPeriodMultiplierLeg1",
                        "floatingRateResetFrequencyPeriodMultiplierLeg2",
                        # --- structural: day count conventions ---
                        "fixedRateDaycountConventionleg1",
                        "floatingRateDaycountConventionLeg2",
                        # --- structural: payment frequency ---
                        "fixedRatePaymentFrequencyPeriodLeg1",
                        "fixedRatePaymentFrequencyPeriodMultiplierLeg1",
                        "floatingRatePaymentFrequencyPeriodLeg2",
                        "floatingRatePaymentFrequencyPeriodMultiplierLeg2",
                        # --- structural: floating reset frequency period ---
                        "floatingRateResetFrequencyPeriodLeg2",
                        # --- legal & settlement ---
                        "settlementCurrencyLeg1",
                        "spreadLeg2",
                        "cleared",
                        # --- regulatory & metadata ---
                        "platformIdentifier",
                        "uniqueProductIdentifier",
                        "disseminationTimestamp",
                        ]

        self.currency = 'COP'

    def get_raw_data(self, date=datetime.datetime.now()):
        payload = self.payload_dtcc(asset='RATES', notional_range=[1, 50e15], currency='COP', date=date)

        r = requests.post(
            self.fred_url,
            json=payload,
            headers=self.headers
        )

        ibr_list = json.loads(r.content)

        return pd.DataFrame.from_records(ibr_list['tradeList'])

    def clean_up(self, s):

        return s.replace('+', '')

    def clean_raw_data_1(self, dataframe, action_type="NEWT", columns=None, eq_operator: bool = True):
        df_cleaned = dataframe.copy(deep=True)

        for x in columns_with_date(columns):
            df_cleaned[x] = df_cleaned[x].apply(str)

        df_cleaned = df_cleaned[df_cleaned['uniqueProductIdentifierUnderlierName'].isin(self.product_name)]
        df_cleaned = df_cleaned[df_cleaned['notionalCurrencyLeg1'] == self.currency]
        df_cleaned = df_cleaned[df_cleaned['notionalCurrencyLeg2'] == self.currency]

        if eq_operator:
            df_cleaned = df_cleaned[df_cleaned['actionType'] == action_type]
        else:
            df_cleaned = df_cleaned[df_cleaned['actionType'] != action_type]

        clean_cols = ['notionalAmountLeg1', 'notionalAmountLeg2']

        for xcol in clean_cols:
            df_cleaned[xcol] = df_cleaned[xcol].str.replace(',', '')
            df_cleaned[xcol] = df_cleaned[xcol].apply(str)
            df_cleaned[xcol] = df_cleaned[xcol].apply(self.clean_up)
            df_cleaned[xcol] = df_cleaned[xcol].astype(float)

            df_cleaned[xcol] = df_cleaned[xcol] / 1e9

        df_cleaned["fixedRateLeg1"] = pd.to_numeric(df_cleaned["fixedRateLeg1"], errors='coerce').fillna(0) * 100
        df_cleaned["fixedRateLeg2"] = pd.to_numeric(df_cleaned["fixedRateLeg2"], errors='coerce').fillna(0) * 100
        zero_indices = df_cleaned[df_cleaned["fixedRateLeg1"] == 0].index
        df_cleaned.loc[zero_indices, "fixedRateLeg1"] = df_cleaned.loc[zero_indices, "fixedRateLeg2"]
        zero_indices = df_cleaned[df_cleaned["fixedRateLeg2"] == 0].index
        df_cleaned.loc[zero_indices, "fixedRateLeg2"] = df_cleaned.loc[zero_indices, "fixedRateLeg1"]

        df_cleaned = df_cleaned[self.columns]

        new_names = {}

        for col_name in df_cleaned.columns:
            new_names[col_name] = str(col_name).lower().replace(' ', '_').replace('-', '_')

        df_cleaned.rename(columns=new_names, inplace=True)

        change_name_direct = {
            'disseminationidentifier': 'dissemination_identifier',
            'originaldisseminationidentifier': 'original_dissemination_identifier',
            'actiontype': 'action_type',
            'eventtimestamp': 'event_timestamp',
            'productname': 'product_name',
            'executiontimestamp': 'execution_timestamp',
            'effectivedate': 'effective_date',
            'expirationdate': 'expiration_date',
            'notionalamountleg1': 'notional_amount_leg_1',
            'notionalamountleg2': 'notional_amount_leg_2',
            'notionalcurrencyleg1': 'notional_currency_leg_1',
            'notionalcurrencyleg2': 'notional_currency_leg_2',
            'fixedrateleg1': 'fixed_rate_leg_1',
            'fixedrateleg2': 'fixed_rate_leg_2',
            'underlieridleg1': 'underlier_id_leg_1',
            'underlieridleg2': 'underlier_id_leg_2',
            'floatingrateresetfrequencyperiodmultiplierleg1': 'floating_rate_reset_frequency_period_multiplier_leg_1',
            'floatingrateresetfrequencyperiodmultiplierleg2': 'floating_rate_reset_frequency_period_multiplier_leg_2',
            # structural: day count conventions
            'fixedratedaycountconventionleg1': 'fixed_rate_daycount_leg_1',
            'floatingratedaycountconventionleg2': 'floating_rate_daycount_leg_2',
            # structural: payment frequency
            'fixedratepaymentfrequencyperiodleg1': 'fixed_pay_freq_period_leg_1',
            'fixedratepaymentfrequencyperiodmultiplierleg1': 'fixed_pay_freq_mult_leg_1',
            'floatingratepaymentfrequencyperiodleg2': 'float_pay_freq_period_leg_2',
            'floatingratepaymentfrequencyperiodmultiplierleg2': 'float_pay_freq_mult_leg_2',
            # structural: floating reset frequency period
            'floatingrateresetfrequencyperiodleg2': 'float_reset_freq_period_leg_2',
            # legal & settlement
            'settlementcurrencyleg1': 'settlement_currency',
            'spreadleg2': 'spread_leg_2',
            'cleared': 'cleared',
            # regulatory & metadata
            'platformidentifier': 'platform',
            'uniqueproductidentifier': 'upi',
            'disseminationtimestamp': 'dissemination_timestamp',
        }

        df_cleaned = df_cleaned.rename(columns=change_name_direct)
        df_cleaned = df_cleaned[list(change_name_direct.values())]
        df_cleaned['product_name'] = self.product_name[0]
        df_cleaned.replace('', np.nan, inplace=True)

        return df_cleaned.replace({pd.NaT: None, np.nan: None})


class IBRSwapCollector_historic(DttcColelctor):
    def __init__(self):
        super().__init__(name='dtcc_ibr')

        self.has_intra_day_prices = True

        # self.api_key = '0ecb1545aa91670f6b492c475b020601'

        # Variables del collector global de DTCC 
        self.fred_url = '2023-ibr-historic.csv'
        # self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        # Variables del collector y busqueda specifica de IBR swaps.
        self.product_name = 'InterestRate:IRSwap:OIS'
        self.columns = ["Dissemination Identifier",
                        "Original Dissemination Identifier",
                        "Action type",
                        "Event timestamp",
                        "Product name",
                        "Execution Timestamp",
                        "Effective Date", "Expiration Date", "Notional amount-Leg 1",
                        "Notional amount-Leg 2", "Notional currency-Leg 1", "Notional currency-Leg 2",
                        "Fixed rate-Leg 1", "Fixed rate-Leg 2", "Underlier ID-Leg 1", "Underlier ID-Leg 2",
                        "Floating rate reset frequency period multiplier-leg 1",
                        "Floating rate reset frequency period multiplier-leg 2"
                        ]

        # self.payload = self.payload_dtcc(asset='IR', notional_range=[0, 50e15], currency='COP')

    def get_raw_data(self, file_path):
        # payload = self.payload_dtcc(asset='IR', notional_range=[0, 50e15], currency='COP')

        # r = requests.post(
        #     self.fred_url, data=urlencode(payload),
        #     headers=self.headers
        # )
        # self.pure_dataframe = pd.read_csv(StringIO(r.text))

        return pd.read_csv(file_path)

    def clean_raw_data_1(self, df_cleaned, action_type="NEWT", columns=None):
        # df_cleaned = self.pure_dataframe.copy(deep=True)

        for x in columns_with_date(columns):
            df_cleaned[x] = df_cleaned[x].apply(str)

        # df_cleaned = df_cleaned[df_cleaned['Product name'] == self.product_name]
        df_cleaned = df_cleaned[df_cleaned['actionType'] == action_type]

        # Remove commas and convert 'Notional amount-Leg 1' to integers
        df_cleaned['notionalAmountLeg1'] = df_cleaned['notionalAmountLeg1'].str.replace(',', '').str.replace('+', '')
        df_cleaned['notionalAmountLeg1'] = df_cleaned['notionalAmountLeg1'].fillna(0).astype(int)

        # df_cleaned['Notional amount-Leg 1'] = df_cleaned['Notional amount-Leg 1'].str.replace('+', '')
        df_cleaned['notionalAmountLeg1'] = df_cleaned['notionalAmountLeg1'] / 1e9

        df_cleaned['notionalAmountLeg2'] = df_cleaned['notionalAmountLeg2'].str.replace(',', '').str.replace('+',
                                                                                                             '')
        df_cleaned['notionalAmountLeg2'] = df_cleaned['notionalAmountLeg2'].fillna(0).astype(int)
        df_cleaned['notionalAmountLeg2'] = df_cleaned['notionalAmountLeg2'] / 1e9
        
        df_cleaned = df_cleaned[self.columns]

        new_names = {}

        for col_name in df_cleaned.columns:
            new_names[col_name] = str(col_name).lower().replace(' ', '_').replace('-', '_')

        df_cleaned.rename(columns=new_names, inplace=True)

        return df_cleaned.replace({pd.NaT: None, np.nan: None})
