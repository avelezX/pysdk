class Marks:
    """
    Access market marks snapshots from the market_marks table.

    Usage:
        x = Xerenity(username, password)
        snap = x.marks.latest()
        snap = x.marks.snapshot("2026-03-03")
        df   = x.marks.history(desde="2026-01-01")
    """

    def __init__(self, connection):
        self._conn = connection

    def snapshot(self, fecha: str) -> dict:
        """
        Fetch the marks snapshot for a specific date.

        Args:
            fecha: ISO date string, e.g. '2026-03-03'

        Returns:
            dict with keys: fecha, fx_spot, sofr_on, ibr, sofr, ndf
            ibr  — dict: {"ibr_1d": 9.636, "ibr_1m": 9.759, "ibr_3m": 10.587, ...}
            sofr — dict: {"1": 3.661, "3": 3.655, "6": 3.594, "12": 3.428, ...}
            ndf  — dict: {"1": {"fwd_pts_cop": 27.25, "F_market": 3830.25, "deval_ea": 8.95}, ...}
            Returns None if no data for that date.

        Example:
            >>> snap = x.marks.snapshot("2026-03-03")
            >>> snap["fx_spot"]
            3803.0
            >>> snap["ibr"]["ibr_3m"]
            10.587
        """
        result = (
            self._conn.supabase.table("market_marks")
            .select("*")
            .eq("fecha", fecha)
            .limit(1)
            .execute()
        )
        data = result.data
        return data[0] if data else None

    def latest(self) -> dict:
        """
        Fetch the most recent marks snapshot.

        Returns:
            dict with keys: fecha, fx_spot, sofr_on, ibr, sofr, ndf
            ibr  — dict: {"ibr_1d": 9.636, "ibr_1m": 9.759, "ibr_3m": 10.587, ...}
            sofr — dict: {"1": 3.661, "3": 3.655, "6": 3.594, "12": 3.428, ...}
            ndf  — dict: {"1": {"fwd_pts_cop": 27.25, "F_market": 3830.25, "deval_ea": 8.95}, ...}
            Returns None if table is empty.

        Example:
            >>> snap = x.marks.latest()
            >>> snap["fecha"]
            '2026-03-03'
            >>> snap["ndf"]["3"]["F_market"]
            3886.75
        """
        result = (
            self._conn.supabase.table("market_marks")
            .select("*")
            .order("fecha", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data
        return data[0] if data else None

    def history(self, desde: str = None, hasta: str = None):
        """
        Retorna el historial de snapshots como un DataFrame.

        Requiere pandas instalado: pip install pandas

        Cada fila es una fecha. Las columnas ibr/sofr/ndf se expanden
        automáticamente: ibr_1m, ibr_3m, sofr_1, sofr_3, ndf_1_F_market, etc.

        Args:
            desde: Fecha inicio (inclusive), formato 'YYYY-MM-DD'. Ej: '2026-01-01'.
            hasta: Fecha fin (inclusive), formato 'YYYY-MM-DD'. Ej: '2026-03-03'.

        Returns:
            pd.DataFrame: Índice = fecha (datetime). Columnas:
                fx_spot, sofr_on,
                ibr_1d, ibr_1m, ibr_3m, ibr_6m, ibr_12m, ibr_2y, ibr_5y, ibr_10y,
                sofr_1, sofr_3, sofr_6, sofr_12, sofr_24, sofr_60, sofr_120, sofr_240,
                ndf_1_fwd_pts_cop, ndf_1_F_market, ndf_1_deval_ea, ... (5 tenores)

        Examples:
            >>> df = x.marks.history()
            >>> df = x.marks.history(desde="2026-01-01")
            >>> df[["ibr_3m", "sofr_3", "fx_spot"]].plot()
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas es requerido para history(). Instala con: pip install pandas")

        q = (
            self._conn.supabase.table("market_marks")
            .select("*")
            .order("fecha", desc=False)
        )
        if desde:
            q = q.gte("fecha", desde)
        if hasta:
            q = q.lte("fecha", hasta)

        data = q.execute().data
        if not data:
            return pd.DataFrame()

        rows = []
        for snap in data:
            row = {
                "fecha": snap["fecha"],
                "fx_spot": snap.get("fx_spot"),
                "sofr_on": snap.get("sofr_on"),
            }
            ibr = snap.get("ibr") or {}
            for k, v in ibr.items():
                row[k] = v

            sofr = snap.get("sofr") or {}
            for k, v in sofr.items():
                row[f"sofr_{k}"] = v

            ndf = snap.get("ndf") or {}
            for tenor, fields in ndf.items():
                if isinstance(fields, dict):
                    for field, val in fields.items():
                        row[f"ndf_{tenor}_{field}"] = val

            rows.append(row)

        df = pd.DataFrame(rows)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.set_index("fecha")
        return df
