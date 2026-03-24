import datetime
import numpy as np
import pandas as pd
import QuantLib as ql
from utilities.date_functions import add_months
from utilities.date_functions import ql_to_datetime
from bond_functions.bond_curve_structures import BondCurve
from bond_functions.tes_quant_lib_details import depo_helpers, tes_quantlib_det


######################################
#  Calculo de curvas implicitas en los TES
######################################
class InflacinImplicita:

    def __init__(self,
                 calc_date=ql.Date.todaysDate(),
                 central_bank_rate=None,
                 tes_table=None,
                 inflation_lag_0=None,
                 last_cpi=None,
                 fixed_rate_excluded_bonds=None,
                 uvr_excluded_bonds=None,
                 col_tes=None,
                 uvr=None
                 ):

        self.calc_date = calc_date
        self.central_bank_rate = central_bank_rate / 100
        self.inflation_print = last_cpi / 100
        self.tes_table = tes_table
        self.fixed_rate_excluded_bonds = fixed_rate_excluded_bonds or []
        self.uvr_excluded_bonds = uvr_excluded_bonds or []
        self.inflation_lag_0 = inflation_lag_0
        self.day_count = ql.Actual365Fixed()
        self.col_tes = col_tes
        self.uvr = uvr

        # Depo helpers for each curve.
        # COP
        depo_maturities = [ql.Period(2, ql.Months)]
        depo_rates = [self.central_bank_rate]
        self.depo_help = depo_helpers(depo_maturities, depo_rates, details=tes_quantlib_det)

        # UVR
        depo_maturities_uvr = [ql.Period(5, ql.Days), ql.Period(2, ql.Months)]
        uvr_ov_deposit_rate = ((1 + self.central_bank_rate) / (1 + self.inflation_print)) - 1
        depo_rates_uvr = [uvr_ov_deposit_rate, uvr_ov_deposit_rate]
        self.depo_help_uvr = depo_helpers(depo_maturities_uvr, depo_rates_uvr, details=tes_quantlib_det)

    def create_date_ranges(self):

        end_date = self.calc_date + ql.Period(10, ql.Years)  # Limit to the next 10 years
        # day_count = ql.Actual365Fixed()
        if self.calc_date.dayOfMonth() < 15:
            init_date = ql.Date(15, self.calc_date.month(), self.calc_date.year())

        else:
            init_date = ql.Date(15, self.calc_date.month(), self.calc_date.year()) + ql.Period(1, ql.Months)

        dates = [init_date]
        for m in range(1, 121):
            current_date = init_date + ql.Period(m, ql.Months)
            current_date = ql.Date(15, current_date.month(), current_date.year())
            dates.append(current_date)
        return dates

    def bond_curve_implied_inflation_mat(self, liquidity_cap_pct=None):
        """
        Extract breakeven (implicit) inflation from TES COP vs TES UVR curves.

        Builds both yield curves from bond helpers, extracts zero rates at
        monthly intervals, and computes breakeven inflation using the Fisher
        equation with continuous compounding:

            inflation = exp(r_nominal - r_real) - 1

        Args:
            liquidity_cap_pct: Optional cap on breakeven inflation (in decimal,
                e.g. 0.06 = 6%). Applied after raw calculation. Use this to
                mitigate the effect of illiquid UVR bonds that inflate the
                long-end breakeven with liquidity premia.
                If None, no cap is applied (raw market breakeven).

        Returns:
            DataFrame with columns: Date, Discount Factors, Zero Rates,
            Discount Factors_UVR, Zero Rates_UVR, Inflacion Implicita,
            Inflacion Implicita Raw (if cap applied)
        """
        # Build COP yield curve (nominal fixed-rate TES)
        cop = BondCurve(currency='COP', country='col', bond_info_df=self.tes_table)
        cop_df = cop.create_df(excluded_bonds=self.fixed_rate_excluded_bonds, colt_tes=self.col_tes)
        helpers = cop.create_bond_helpers(cop_df, excluded_bonds=self.fixed_rate_excluded_bonds)
        cop_yield_curve = cop.yield_curve_ql(self.calc_date, helpers, self.depo_help)

        # Build UVR yield curve (inflation-indexed TES)
        uvr_bc = BondCurve('UVR', 'col', bond_info_df=self.tes_table)
        uvr_df = uvr_bc.create_df(excluded_bonds=self.uvr_excluded_bonds, colt_tes=self.col_tes)
        helpers_uvr = uvr_bc.create_bond_helpers(uvr_df, excluded_bonds=self.uvr_excluded_bonds)
        uvr_yield_curve = uvr_bc.yield_curve_ql(self.calc_date, helpers_uvr, self.depo_help_uvr)

        # Extract rates at each date and compute breakeven inflation
        dates = self.create_date_ranges()
        date_df = pd.DataFrame(data={'Date': dates})

        cop_max_t = cop_yield_curve.maxTime()
        uvr_max_t = uvr_yield_curve.maxTime()

        date_df['Discount Factors'] = date_df['Date'].apply(
            lambda d: cop_yield_curve.discount(d) if cop_yield_curve.timeFromReference(d) <= cop_max_t else None)
        date_df['Zero Rates'] = date_df['Date'].apply(
            lambda d: cop_yield_curve.zeroRate(d, self.day_count, ql.Continuous).rate()
            if cop_yield_curve.timeFromReference(d) <= cop_max_t else None)
        date_df['Discount Factors_UVR'] = date_df['Date'].apply(
            lambda d: uvr_yield_curve.discount(d) if uvr_yield_curve.timeFromReference(d) <= uvr_max_t else None)
        date_df['Zero Rates_UVR'] = date_df['Date'].apply(
            lambda d: uvr_yield_curve.zeroRate(d, self.day_count, ql.Continuous).rate()
            if uvr_yield_curve.timeFromReference(d) <= uvr_max_t else None)

        # Fisher equation with continuous rates:
        # exp(r_nominal) = exp(r_real) * (1 + inflation)
        # inflation = exp(r_nominal - r_real) - 1
        date_df['Inflacion Implicita'] = np.exp(
            date_df['Zero Rates'] - date_df['Zero Rates_UVR']
        ) - 1

        # Apply liquidity cap if specified
        if liquidity_cap_pct is not None:
            date_df['Inflacion Implicita Raw'] = date_df['Inflacion Implicita']
            date_df['Inflacion Implicita'] = date_df['Inflacion Implicita'].clip(upper=liquidity_cap_pct)
            capped_count = (date_df['Inflacion Implicita Raw'] > liquidity_cap_pct).sum()
            if capped_count > 0:
                print(f"  Liquidity cap: {capped_count} points capped at {liquidity_cap_pct*100:.1f}%")

        date_df['Date'] = date_df['Date'] - ql.Period('1m')

        return date_df

    def create_cpi_index(self):
        """
        Build a forward CPI index by chaining historical CPI with
        the implicit inflation from the TES breakeven curve.

        Historical CPI dates (1st of month) are normalized to the 15th
        for alignment with the inflation curve dates. Missing months
        are interpolated linearly.

        Forward projection:
            CPI(t) = CPI(t - 12m) * (1 + breakeven_inflation(t))

        The projection iterates chronologically so that each new CPI
        value is available for the next year's lookup.

        Returns:
            dict with 'total_cpi', 'total_cpi_yoy', 'total_cpi_monthly'
        """
        df = self.inflation_lag_0.copy()
        date_df = self.bond_curve_implied_inflation_mat()

        df['Total'] = df['cpi_index']
        df['fecha'] = pd.to_datetime(df['fecha'])
        df.set_index('fecha', inplace=True)

        df_cpi = pd.DataFrame(df['Total'].dropna())
        df_cpi.rename(columns={'Total': 'indice'}, inplace=True)

        # Normalize dates from 1st to 15th of each month
        df_cpi.index = pd.to_datetime(
            df_cpi.index.year * 10000 + df_cpi.index.month * 100 + 15,
            format='%Y%m%d',
        )
        df_cpi = df_cpi[~df_cpi.index.duplicated(keep='last')]
        df_cpi = df_cpi.sort_index()

        # Fill any missing months via linear interpolation
        full_range = pd.date_range(
            start=df_cpi.index.min(),
            end=df_cpi.index.max(),
            freq='MS',  # month start
        )
        # Shift to 15th
        full_range_15 = full_range + pd.DateOffset(days=14)
        df_cpi = df_cpi.reindex(df_cpi.index.union(full_range_15))
        df_cpi = df_cpi.sort_index()
        df_cpi['indice'] = df_cpi['indice'].interpolate(method='linear')

        total_cpi = df_cpi['indice']

        # Forward projection: CPI(t) = CPI(t-1Y) * (1 + inflation(t))
        # Iterate chronologically so projected values are available for next lookups
        projection_dates = sorted(date_df['Date'].tolist(), key=lambda d: (d.year(), d.month(), d.dayOfMonth()))

        projected_count = 0
        skipped_count = 0
        for d in projection_dates:
            d_dt = ql_to_datetime(d)
            d_1y = ql_to_datetime(d - ql.Period('1y'))

            # Find CPI 12 months ago (nearest within 20 days)
            if d_1y in total_cpi.index:
                f_1 = total_cpi[d_1y]
            else:
                # Find nearest date in index
                idx_arr = total_cpi.index
                diffs = abs(idx_arr - pd.Timestamp(d_1y))
                nearest_idx = diffs.argmin()
                if diffs[nearest_idx].days <= 20:
                    f_1 = total_cpi.iloc[nearest_idx]
                else:
                    skipped_count += 1
                    continue

            # Get breakeven inflation for this date
            mask = date_df['Date'] == d
            if not mask.any():
                skipped_count += 1
                continue
            infl = date_df.loc[mask, 'Inflacion Implicita'].values[0]
            if pd.isna(infl):
                skipped_count += 1
                continue

            total_cpi.loc[d_dt] = f_1 * (1 + infl)
            projected_count += 1

        total_cpi = total_cpi.sort_index()
        if skipped_count > 0:
            print(f"  CPI projection: {projected_count} projected, {skipped_count} skipped (missing lookback data)")

        total_cpi = pd.DataFrame(total_cpi)
        total_cpi_monthly = total_cpi.pct_change(periods=1)
        total_cpi_yoy = total_cpi.pct_change(periods=12)

        return {'total_cpi': total_cpi, 'total_cpi_yoy': total_cpi_yoy, 'total_cpi_monthly': total_cpi_monthly}

    def calculo_serie_uvr(self, cpi_serie=None):
        if cpi_serie is None:
            raise ValueError('No CPI index data provided for UVR projection')

        indice = cpi_serie
        indice.index = pd.to_datetime(indice.index).date

        uvr = self.uvr.copy(deep=True)
        uvr['fecha'] = pd.to_datetime(uvr['fecha'])
        if 'id_serie' in uvr.columns:
            uvr.drop('id_serie', axis=1, inplace=True)
        uvr.set_index('fecha', inplace=True)
        uvr.index = pd.to_datetime(uvr.index).date

        init_date = max(uvr.index)
        errors = []
        for m in range(0, 120):
            current_date = add_months(init_date, m).date()
            next_date = add_months(current_date, 1).date()
            try:
                current_index_value = indice.loc[current_date]['indice']
                next_index_value = indice.loc[next_date]['indice']
                valor_uvr = uvr.loc[current_date]['valor']
                uvr.loc[next_date] = valor_uvr * next_index_value / current_index_value
            except KeyError as e:
                errors.append(f"Month {m}: missing CPI data for {e}")
                continue
            except Exception as e:
                errors.append(f"Month {m} ({current_date}): {type(e).__name__}: {e}")
                continue

        if errors:
            print(f"UVR projection: {len(errors)} errors out of 120 months:")
            for err in errors[:5]:
                print(f"  - {err}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")

        return uvr
