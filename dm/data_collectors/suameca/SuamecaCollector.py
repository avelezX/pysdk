import requests
import pandas as pd
from datetime import datetime
from data_collectors.DataCollector import DataCollector


class SuamecaCollector(DataCollector):
    """
    Collector for BanRep's SUAMECA portal (suameca.banrep.gov.co).
    Replaces the old totoro.banrep.gov.co SDMX API which is now dead (404).

    Uses the consultaInformacionSerie endpoint which returns full historical
    data for any series in the SUAMECA catalog (858+ series).

    Data format: each series contains a 'data' array of [timestamp_ms, value] pairs.
    """

    def __init__(self):
        super().__init__(name='suameca')

        self.session = requests.session()
        self.base_url = (
            'https://suameca.banrep.gov.co/estadisticas-economicas-back'
            '/rest/estadisticaEconomicaRestService'
        )
        self.session.headers.update({
            'referer': 'https://suameca.banrep.gov.co/estadisticas-economicas/'
        })

    def fetch_series(self, suameca_ids):
        """
        Fetch one or more series from SUAMECA.

        Args:
            suameca_ids: single int or list of ints (SUAMECA catalog IDs)

        Returns:
            list of series dicts, each with 'id', 'nombre', 'data', etc.
        """
        if isinstance(suameca_ids, int):
            suameca_ids = [suameca_ids]

        ids_str = ','.join(str(i) for i in suameca_ids)
        url = f'{self.base_url}/consultaInformacionSerie?idSerie={ids_str}'

        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        return response.json()

    def series_to_dataframe(self, series_data, internal_id):
        """
        Convert a single SUAMECA series response to a DataFrame
        with columns [id_serie, fecha, valor].

        Args:
            series_data: dict with 'data' key containing [[timestamp_ms, value], ...]
            internal_id: our internal serie ID for banrep_series_value_v2

        Returns:
            pandas DataFrame with columns [id_serie, fecha, valor]
        """
        raw_data = series_data.get('data', [])

        rows = []
        for point in raw_data:
            if len(point) >= 2 and point[1] is not None:
                ts_ms = point[0]
                value = point[1]
                fecha = datetime.utcfromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d')
                rows.append([internal_id, fecha, value])

        if not rows:
            return pd.DataFrame(columns=['id_serie', 'fecha', 'valor'])

        df = pd.DataFrame(rows, columns=['id_serie', 'fecha', 'valor'])
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

        return df

    def get_series_data(self, suameca_id, internal_id):
        """
        Fetch a single series and return as DataFrame.

        Args:
            suameca_id: SUAMECA catalog ID
            internal_id: our internal serie ID

        Returns:
            pandas DataFrame with columns [id_serie, fecha, valor]
        """
        try:
            result = self.fetch_series(suameca_id)

            if not result or not isinstance(result, list) or len(result) == 0:
                print(f'No data returned for SUAMECA ID {suameca_id}')
                return pd.DataFrame(columns=['id_serie', 'fecha', 'valor'])

            # Find the matching series in the response
            for series in result:
                if series.get('id') == suameca_id:
                    df = self.series_to_dataframe(series, internal_id)
                    print(f'SUAMECA {suameca_id} -> {len(df)} rows for internal ID {internal_id}')
                    return df

            # If exact match not found, use first series
            df = self.series_to_dataframe(result[0], internal_id)
            print(f'SUAMECA {suameca_id} -> {len(df)} rows for internal ID {internal_id}')
            return df

        except Exception as error:
            print(f'Error fetching SUAMECA ID {suameca_id}: {error}')
            return pd.DataFrame(columns=['id_serie', 'fecha', 'valor'])

    def get_batch_series_data(self, series_mapping):
        """
        Fetch multiple series in a single API call and return as a dict of DataFrames.

        Args:
            series_mapping: list of dicts with 'suameca_id' and 'internal_id'

        Returns:
            dict mapping internal_id -> DataFrame
        """
        suameca_ids = [s['suameca_id'] for s in series_mapping]
        id_map = {s['suameca_id']: s['internal_id'] for s in series_mapping}

        try:
            result = self.fetch_series(suameca_ids)

            if not result or not isinstance(result, list):
                print(f'No data returned for batch: {suameca_ids}')
                return {}

            frames = {}
            for series in result:
                sid = series.get('id')
                if sid in id_map:
                    internal_id = id_map[sid]
                    df = self.series_to_dataframe(series, internal_id)
                    frames[internal_id] = df

            return frames

        except Exception as error:
            print(f'Error in batch fetch: {error}')
            return {}
