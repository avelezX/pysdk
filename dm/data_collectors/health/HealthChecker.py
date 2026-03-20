import requests
from datetime import datetime, timedelta


class HealthChecker:
    """
    Checks data freshness across all Xerenity tables by querying
    Supabase REST API for the most recent date in each table.
    """

    def __init__(self, supabase_url, supabase_key, collector_bearer):
        self.base_url = f'{supabase_url}/rest/v1'
        self.headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {collector_bearer}',
            'Accept-Profile': 'xerenity'
        }

        # Define all tables to monitor
        # (label, table, date_column, max_age_hours, filter_params, weekday_only)
        self.checks = [
            # IBR & COP market data (daily, weekdays)
            ('IBR Swaps', 'ibr_swaps', 'event_timestamp', 24, None, True),
            ('IBR Loan Curve (MV)', 'ibr_quotes_curve', 'fecha', 48, None, True),
            ('TRM (USD:COP)', 'currency', 'time', 48, {'currency': 'eq.USD:COP'}, True),
            ('FIC Fondos', 'fic_v2', 'fecha_corte', 48, None, True),

            # BanRep series (daily, weekdays via SUAMECA)
            ('IBR 1D (serie 9)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.9'}, True),
            ('IBR 1M (serie 11)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.11'}, True),
            ('IBR 3M (serie 13)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.13'}, True),
            ('IBR 6M (serie 15)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.15'}, True),
            ('IBR 12M (serie 17)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.17'}, True),
            ('TPM (serie 8)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.8'}, True),
            ('UVR (serie 19)', 'banrep_series_value_v2', 'fecha', 48, {'id_serie': 'eq.19'}, True),
            ('IPC Var (serie 7)', 'banrep_series_value_v2', 'fecha', 720, {'id_serie': 'eq.7'}, False),

            # Credit & rates
            ('Interes Creditos', 'interes_creditos', 'fecha_corte', 48, None, True),
            ('Tasa Usura', 'tasa_usura', 'fecha', 744, None, False),

            # US market data (daily)
            ('SOFR Swap Curve', 'sofr_swap_curve', 'fecha', 48, None, True),
            ('US Ref Rates (SOFR)', 'us_reference_rates', 'fecha', 48, {'rate_type': 'eq.SOFR'}, True),
            ('UST Yield Curve', 'ust_yield_curve', 'fecha', 48, {'curve_type': 'eq.NOMINAL'}, True),

            # Weekly/monthly
            ('EMBI', 'embi', 'time', 168, None, False),
            ('CB Rates (BIS)', 'cb_rates', 'fecha', 900, None, False),

            # Crypto (daily, including weekends)
            ('Crypto BTC:USD', 'currency', 'time', 48, {'currency': 'eq.BTC:USD'}, False),
            ('Crypto ETH:USD', 'currency', 'time', 48, {'currency': 'eq.ETH:USD'}, False),

            # BCRP Peru (daily, weekdays)
            ('PE TC Interbancario', 'bcrp_series_value', 'fecha', 48, {'id_serie': 'eq.101'}, True),
            ('PE Tasa Interbancaria', 'bcrp_series_value', 'fecha', 48, {'id_serie': 'eq.105'}, True),
            ('PE Tasa Referencia', 'bcrp_series_value', 'fecha', 48, {'id_serie': 'eq.107'}, True),
            ('PE Bono 10Y PEN', 'bcrp_series_value', 'fecha', 48, {'id_serie': 'eq.110'}, True),
            ('PE IPC Lima', 'bcrp_series_value', 'fecha', 720, {'id_serie': 'eq.130'}, False),
        ]

    def _get_latest_date(self, table, date_column, filter_params=None):
        """Query latest date from a table via Supabase REST API."""
        params = {
            'select': date_column,
            f'order': f'{date_column}.desc',
            'limit': '1'
        }
        if filter_params:
            for key, value in filter_params.items():
                params[key] = value

        try:
            resp = requests.get(
                f'{self.base_url}/{table}',
                headers=self.headers,
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data and len(data) > 0:
                date_str = data[0][date_column]
                if date_str:
                    # Handle both "2026-02-19" and "2026-02-19T00:00:00" formats
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
            return None

        except Exception as e:
            print(f'Error checking {table}: {e}')
            return None

    def _calculate_business_hours(self, latest_date, now):
        """
        Calculate age in hours, skipping weekends for weekday-only tables.
        If latest_date is a Friday and now is Monday, the effective age
        is ~24h (not 72h).
        """
        if latest_date is None:
            return float('inf')

        total_hours = (now - latest_date).total_seconds() / 3600

        # Count weekend days between latest_date and now
        weekend_days = 0
        current = latest_date
        while current < now:
            if current.weekday() >= 5:  # Saturday=5, Sunday=6
                weekend_days += 1
            current += timedelta(days=1)

        business_hours = total_hours - (weekend_days * 24)
        return max(business_hours, 0)

    def check_all(self):
        """Run all freshness checks and return results."""
        now = datetime.utcnow()
        results = []

        for label, table, date_col, max_age, filters, weekday_only in self.checks:
            latest = self._get_latest_date(table, date_col, filters)

            if latest is None:
                age_hours = float('inf')
            elif weekday_only:
                age_hours = self._calculate_business_hours(latest, now)
            else:
                age_hours = (now - latest).total_seconds() / 3600

            # Determine status
            if age_hours == float('inf'):
                status = 'error'
            elif age_hours > max_age:
                status = 'stale'
            elif age_hours > max_age * 0.75:
                status = 'warning'
            else:
                status = 'ok'

            results.append({
                'label': label,
                'table': table,
                'latest_date': latest.strftime('%Y-%m-%d') if latest else 'N/A',
                'age_hours': round(age_hours, 1) if age_hours != float('inf') else None,
                'max_age_hours': max_age,
                'status': status
            })

        return results
