"""
Collector for Camacol construction sector series.
Reads series_camacol_completo.xlsx and extracts 29 individual time series
in (id_serie, fecha, valor) format for insertion into camacol_series_value.

Series mapping:
  1-5:   PIB real values (quarterly)
  6-10:  PIB growth rates (quarterly)
  11-14: ICOCED cost index (monthly)
  15-18: Cemento production/dispatch (monthly)
  19-26: Financiacion mortgage disbursements (monthly)
  27-29: IPVN housing price index (variable)
"""
import pandas as pd


class CamacolCollector:

    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.xls = pd.ExcelFile(excel_path)

    def _find_sheet(self, keyword):
        for s in self.xls.sheet_names:
            if keyword in s:
                return s
        return None

    def _quarter_to_date(self, period_str):
        """Convert quarterly period like '1977-I' to date string '1977-03-31'."""
        period_str = str(period_str).strip()
        parts = period_str.split('-')
        if len(parts) != 2:
            return None
        year = parts[0].strip()
        quarter = parts[1].strip().upper()
        quarter_map = {'I': '03-31', 'II': '06-30', 'III': '09-30', 'IV': '12-31'}
        suffix = quarter_map.get(quarter)
        if not suffix or not year.isdigit():
            return None
        return f'{year}-{suffix}'

    def extract_pib(self):
        """PIB Construccion - quarterly since 1977. Returns list of DataFrames for series 1-10."""
        name = self._find_sheet('CIF_PIB construcci')
        if not name:
            print('Sheet CIF_PIB not found')
            return []

        df = pd.read_excel(self.xls, name, header=None)

        # Columns: real values (IDs 1-5), growth rates (IDs 6-10)
        real_cols = [(2, 1), (3, 2), (4, 3), (5, 4), (6, 5)]  # (excel_col, id_serie)
        var_cols = [(7, 6), (8, 7), (9, 8), (10, 9), (11, 10)]

        all_rows = {sid: [] for _, sid in real_cols + var_cols}

        for i in range(6, len(df)):
            period = df.iloc[i, 1]
            if pd.isna(period):
                continue
            fecha = self._quarter_to_date(period)
            if not fecha:
                continue

            for col_idx, sid in real_cols + var_cols:
                v = df.iloc[i, col_idx]
                if pd.notna(v) and isinstance(v, (int, float)):
                    all_rows[sid].append([sid, fecha, float(v)])

        frames = []
        for sid in sorted(all_rows.keys()):
            if all_rows[sid]:
                frame = pd.DataFrame(all_rows[sid], columns=['id_serie', 'fecha', 'valor'])
                frames.append(frame)
        return frames

    def extract_icoced(self):
        """ICOCED cost index - monthly since 2022. Returns list of DataFrames for series 11-14."""
        name = self._find_sheet('CIF_ICOCED 1')
        if not name:
            print('Sheet CIF_ICOCED not found')
            return []

        df = pd.read_excel(self.xls, name, header=None)
        # Col 1: date, Col 2: ICOCED Total (11), Col 3: Var mensual (12),
        # Col 4: Var año corrido (13), Col 5: Var anual (14)
        col_map = [(2, 11), (3, 12), (4, 13), (5, 14)]
        all_rows = {sid: [] for _, sid in col_map}

        for i in range(5, len(df)):
            fecha_raw = df.iloc[i, 1]
            if pd.isna(fecha_raw):
                continue
            fecha = str(fecha_raw)[:10]
            if not any(c.isdigit() for c in fecha):
                continue

            for col_idx, sid in col_map:
                v = df.iloc[i, col_idx]
                if pd.notna(v) and isinstance(v, (int, float)):
                    all_rows[sid].append([sid, fecha, float(v)])

        frames = []
        for sid in sorted(all_rows.keys()):
            if all_rows[sid]:
                frames.append(pd.DataFrame(all_rows[sid], columns=['id_serie', 'fecha', 'valor']))
        return frames

    def extract_cemento(self):
        """Cemento - monthly since 1990. Returns list of DataFrames for series 15-18."""
        name = self._find_sheet('CIF_Cemento 1')
        if not name:
            print('Sheet CIF_Cemento not found')
            return []

        df = pd.read_excel(self.xls, name, header=None)
        # Col 1: date, Col 2: Produccion (15), Col 3: Despachos (16),
        # Col 4: Var Produccion (17), Col 5: Var Despachos (18)
        col_map = [(2, 15), (3, 16), (4, 17), (5, 18)]
        all_rows = {sid: [] for _, sid in col_map}

        for i in range(5, len(df)):
            fecha_raw = df.iloc[i, 1]
            if pd.isna(fecha_raw):
                continue
            fecha = str(fecha_raw)[:10]
            if not any(c.isdigit() for c in fecha):
                continue

            for col_idx, sid in col_map:
                v = df.iloc[i, col_idx]
                if pd.notna(v) and isinstance(v, (int, float)):
                    all_rows[sid].append([sid, fecha, float(v)])

        frames = []
        for sid in sorted(all_rows.keys()):
            if all_rows[sid]:
                frames.append(pd.DataFrame(all_rows[sid], columns=['id_serie', 'fecha', 'valor']))
        return frames

    def extract_financiacion(self):
        """Financiacion - monthly since 2002. Returns list of DataFrames for series 19-26."""
        name = self._find_sheet('CIF_Financiaci')
        if not name:
            print('Sheet CIF_Financiacion not found')
            return []

        df = pd.read_excel(self.xls, name, header=None)
        # Col 1: date, Cols 2-9: 8 financing series
        # Constr NoVIS pesos(19), NoVIS UVR(20), VIS pesos(21), VIS UVR(22)
        # Adq NoVIS pesos(23), NoVIS UVR(24), VIS pesos(25), VIS UVR(26)
        col_map = [(2, 19), (3, 20), (4, 21), (5, 22), (6, 23), (7, 24), (8, 25), (9, 26)]
        all_rows = {sid: [] for _, sid in col_map}

        for i in range(6, len(df)):
            fecha_raw = df.iloc[i, 1]
            if pd.isna(fecha_raw):
                continue
            fecha = str(fecha_raw)[:10]
            if not any(c.isdigit() for c in fecha):
                continue

            for col_idx, sid in col_map:
                v = df.iloc[i, col_idx]
                if pd.notna(v) and isinstance(v, (int, float)):
                    all_rows[sid].append([sid, fecha, float(v)])

        frames = []
        for sid in sorted(all_rows.keys()):
            if all_rows[sid]:
                frames.append(pd.DataFrame(all_rows[sid], columns=['id_serie', 'fecha', 'valor']))
        return frames

    def extract_ipvn(self):
        """IPVN housing price index. Returns list of DataFrames for series 27-29."""
        name = self._find_sheet('CIF_IPVN 1')
        if not name:
            print('Sheet CIF_IPVN not found')
            return []

        df = pd.read_excel(self.xls, name, header=None)
        # Col 1: date, Col 2: Indice Nacional (27), Col 3: Var trimestral (28), Col 4: Var anual (29)
        col_map = [(2, 27), (3, 28), (4, 29)]
        all_rows = {sid: [] for _, sid in col_map}

        # Find data start row (look for dates)
        start_row = 6
        for i in range(4, 10):
            val = df.iloc[i, 1]
            if pd.notna(val) and '20' in str(val)[:10]:
                start_row = i
                break

        for i in range(start_row, len(df)):
            fecha_raw = df.iloc[i, 1]
            if pd.isna(fecha_raw):
                continue
            fecha = str(fecha_raw)[:10]
            if not any(c.isdigit() for c in fecha):
                continue

            for col_idx, sid in col_map:
                v = df.iloc[i, col_idx]
                if pd.notna(v) and isinstance(v, (int, float)):
                    all_rows[sid].append([sid, fecha, float(v)])

        frames = []
        for sid in sorted(all_rows.keys()):
            if all_rows[sid]:
                frames.append(pd.DataFrame(all_rows[sid], columns=['id_serie', 'fecha', 'valor']))
        return frames

    def extract_all(self):
        """Extract all 29 series from the Excel file.
        Returns a list of DataFrames, each with columns [id_serie, fecha, valor]."""
        all_frames = []

        extractors = [
            ('PIB', self.extract_pib),
            ('ICOCED', self.extract_icoced),
            ('Cemento', self.extract_cemento),
            ('Financiacion', self.extract_financiacion),
            ('IPVN', self.extract_ipvn),
        ]

        for name, extractor in extractors:
            try:
                frames = extractor()
                print(f'{name}: {len(frames)} series extracted')
                for f in frames:
                    sid = f["id_serie"].iloc[0]
                    print(f'  Serie {sid}: {len(f)} rows ({f["fecha"].iloc[0]} to {f["fecha"].iloc[-1]})')
                all_frames.extend(frames)
            except Exception as e:
                print(f'Error extracting {name}: {e}')

        print(f'\nTotal: {len(all_frames)} series extracted')
        return all_frames
