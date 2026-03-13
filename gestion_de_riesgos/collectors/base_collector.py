"""
Collectors de precios para el modulo de gestion de riesgos.
Integrados desde Risk-management/futuros_data/collectors.

Fuentes de datos:
- Interactive Brokers (ib_async): Futuros de MAIZ (ZC), AZUCAR (SB), CACAO (CC)
- Archivos JSON locales: Datos historicos mantenidos por los notebooks de IB
- Xerenity API / Excel: TRM (USD/COP)

Arquitectura:
- Los notebooks de IB (maiz.ipynb, azucar.ipynb, cacao.ipynb) mantienen archivos JSON
  con datos historicos por contrato en la ruta DATA_DIR.
- Este modulo lee esos JSON para alimentar el VaR calculator.
- Tambien puede conectarse directamente a IB para actualizar datos on-demand.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import json
import re

# ==================== CONFIGURACION ====================
DATA_DIR = Path(
    r"C:\Users\DanielAristizabal\Saman\Banca de Inversión - Documents"
    r"\Super de Alimentos\Gestión de riesgo\Data"
)

JSON_PATHS = {
    'MAIZ': DATA_DIR / 'data_zc1.json',
    'AZUCAR': DATA_DIR / 'data_sb.json',
    'CACAO': DATA_DIR / 'data_cc.json',
}

TRM_EXCEL_PATH = DATA_DIR / 'trm.xlsx'
TRM_XERENITY_TICKER = "10180ef6704e932b6dff09c0e1990ce6"

IB_HOST = "127.0.0.1"
IB_PORT = 7496   # 7497 para paper trading
# =======================================================

# Config de contratos por commodity
COMMODITY_CONFIG = {
    'MAIZ': {
        'symbol': 'ZC',
        'exchanges': ['CBOT', 'ECBOT'],
        'months': {'H': '03', 'K': '05', 'N': '07', 'U': '09', 'Z': '12'},
        'code_pattern': r'ZC[HKNUZ]\d{2}',
    },
    'AZUCAR': {
        'symbol': 'SB',
        'exchanges': ['NYBOT', 'ICEUS'],
        'months': {'H': '03', 'K': '05', 'N': '07', 'V': '10'},
        'code_pattern': r'SB[HKNV]\d{1,2}',
    },
    'CACAO': {
        'symbol': 'CC',
        'exchanges': ['NYBOT', 'ICEUS'],
        'months': {'H': '03', 'K': '05', 'N': '07', 'U': '09', 'Z': '12'},
        'code_pattern': r'CC[HKNUZ]\d{2}',
    },
}


# ==================== UTILIDADES ====================

def _code_to_yyyymm(code: str, config: dict) -> str:
    """Convierte codigo de contrato (ej: ZCH26, SBH6) a YYYYMM."""
    symbol = config['symbol']
    month_letters = config['months']
    month_num_to_letter = {v: k for k, v in month_letters.items()}
    letters_regex = ''.join(month_letters.keys())

    m = re.fullmatch(rf"{symbol}([{letters_regex}])(\d{{1,2}})", code.strip().upper())
    if not m:
        raise ValueError(f"Codigo invalido {symbol}: {code}")

    letter, yy = m.groups()
    if len(yy) == 1:
        year = 2020 + int(yy)
    else:
        yy_i = int(yy)
        year = 2000 + yy_i if yy_i <= 79 else 1900 + yy_i

    mm = month_letters[letter]
    return f"{year}{mm}"


def _load_json(path: Path) -> dict:
    """Lee archivo JSON de datos de futuros."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _pick_front_contract(db: dict, config: dict) -> str:
    """
    Selecciona el contrato front (vigente mas cercano con datos recientes).
    Logica basada en maiz.ipynb: pick_front_contract_async.
    """
    pattern = config['code_pattern']
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    contracts = []
    for code in db.keys():
        if re.fullmatch(pattern, code):
            try:
                yyyymm = _code_to_yyyymm(code, config)
                contracts.append((code, yyyymm))
            except ValueError:
                continue

    if not contracts:
        return ""

    # Filtrar contratos cuyo mes de expiracion >= mes actual
    current_yyyymm = today.strftime("%Y%m")
    active = [(code, ym) for code, ym in contracts if ym >= current_yyyymm]

    if not active:
        # Si no hay activos, tomar el mas reciente
        active = contracts

    # Ordenar por fecha de expiracion y tomar el mas cercano
    active.sort(key=lambda x: x[1])

    # Preferir el que tenga datos mas recientes
    best_code = active[0][0]
    best_last_date = ""
    for code, ym in active[:3]:  # Revisar los 3 mas cercanos
        bars = db.get(code, [])
        if bars:
            last = max(r["date"] for r in bars)
            if last > best_last_date:
                best_last_date = last
                best_code = code

    return best_code


def _extract_price_series(db: dict, contract_code: str,
                          start_date: str = None) -> pd.DataFrame:
    """Extrae serie de precios close de un contrato del JSON."""
    bars = db.get(contract_code, [])
    if not bars:
        return pd.DataFrame()

    df = pd.DataFrame(bars)
    df = df[['date', 'close']].dropna()
    df = df.drop_duplicates('date').sort_values('date').reset_index(drop=True)

    if start_date:
        df = df[df['date'] >= start_date]

    return df


# ==================== COLLECTORS ====================

class BaseCollector(ABC):
    """Clase base para todos los collectors de precios."""

    def __init__(self, asset_name: str):
        self.asset_name = asset_name

    @abstractmethod
    def fetch_prices(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Obtiene precios historicos.

        Returns:
            DataFrame con columnas: ['date', 'close']
        """
        pass

    def collect_and_store(self, start_date: str, end_date: str) -> int:
        """Obtiene precios y los almacena en Supabase."""
        from gestion_de_riesgos.db_risk import upsert_risk_prices

        prices_df = self.fetch_prices(start_date, end_date)
        if prices_df.empty:
            return 0

        records = [
            {
                'date': str(row['date']),
                'asset': self.asset_name,
                'price': float(row['close']),
                'collected_at': datetime.now().isoformat(),
            }
            for _, row in prices_df.iterrows()
        ]

        upsert_risk_prices(records)
        return len(records)


class FuturesJSONCollector(BaseCollector):
    """
    Collector que lee datos de futuros desde archivos JSON
    mantenidos por los notebooks de Interactive Brokers.

    Selecciona automaticamente el contrato front (mas liquido/cercano).
    """

    def __init__(self, asset_name: str, json_path: Path, config: dict):
        super().__init__(asset_name)
        self.json_path = json_path
        self.config = config

    def fetch_prices(self, start_date: str, end_date: str) -> pd.DataFrame:
        db = _load_json(self.json_path)
        if not db:
            return pd.DataFrame()

        contract = _pick_front_contract(db, self.config)
        if not contract:
            return pd.DataFrame()

        df = _extract_price_series(db, contract, start_date)
        if df.empty:
            return df

        df = df[df['date'] <= end_date]
        return df

    def get_available_contracts(self) -> list[str]:
        """Lista todos los contratos disponibles en el JSON."""
        db = _load_json(self.json_path)
        pattern = self.config['code_pattern']
        return sorted([k for k in db.keys() if re.fullmatch(pattern, k)])

    def fetch_contract_prices(self, contract_code: str,
                              start_date: str = None) -> pd.DataFrame:
        """Obtiene precios de un contrato especifico."""
        db = _load_json(self.json_path)
        return _extract_price_series(db, contract_code, start_date)

    def get_front_contract(self) -> str:
        """Retorna el codigo del contrato front actual."""
        db = _load_json(self.json_path)
        return _pick_front_contract(db, self.config)


class CornCollector(FuturesJSONCollector):
    """Collector para futuros de Maiz (ZC) - CBOT via IB"""

    def __init__(self):
        super().__init__(
            'MAIZ',
            JSON_PATHS['MAIZ'],
            COMMODITY_CONFIG['MAIZ'],
        )


class SugarCollector(FuturesJSONCollector):
    """Collector para futuros de Azucar (SB) - NYBOT/ICEUS via IB"""

    def __init__(self):
        super().__init__(
            'AZUCAR',
            JSON_PATHS['AZUCAR'],
            COMMODITY_CONFIG['AZUCAR'],
        )


class CocoaCollector(FuturesJSONCollector):
    """Collector para futuros de Cacao (CC) - NYBOT/ICEUS via IB"""

    def __init__(self):
        super().__init__(
            'CACAO',
            JSON_PATHS['CACAO'],
            COMMODITY_CONFIG['CACAO'],
        )


class TRMCollector(BaseCollector):
    """
    Collector para TRM (USD/COP).
    Lee desde el Excel mantenido por trm.ipynb (fuente: Xerenity/BanRep).
    Fallback a la API de Xerenity directamente.
    """

    def __init__(self):
        super().__init__('USD')

    def fetch_prices(self, start_date: str, end_date: str) -> pd.DataFrame:
        # Primero intentar desde Excel (mas rapido, ya mantenido por notebook)
        try:
            df = self._fetch_from_excel(start_date, end_date)
            if not df.empty:
                return df
        except Exception:
            pass

        # Fallback: Xerenity API directamente
        try:
            return self._fetch_from_xerenity(start_date, end_date)
        except Exception:
            return pd.DataFrame()

    def _fetch_from_excel(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Lee TRM desde el Excel mantenido por trm.ipynb."""
        if not TRM_EXCEL_PATH.exists():
            raise FileNotFoundError(f"No existe {TRM_EXCEL_PATH}")

        df = pd.read_excel(TRM_EXCEL_PATH, sheet_name="sheet1")
        df.columns = [c.lower() for c in df.columns]

        df["fecha"] = pd.to_datetime(df["fecha"])

        if df["precio"].dtype == object:
            df["precio"] = (
                df["precio"].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce")

        df = df.dropna(subset=["fecha", "precio"]).sort_values("fecha")
        df = df.drop_duplicates("fecha", keep="last")

        # Filtrar rango
        df = df[
            (df["fecha"] >= pd.to_datetime(start_date))
            & (df["fecha"] <= pd.to_datetime(end_date))
        ]

        result = pd.DataFrame({
            'date': df["fecha"].dt.strftime('%Y-%m-%d'),
            'close': df["precio"].values,
        })

        return result.reset_index(drop=True)

    def _fetch_from_xerenity(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene TRM desde Xerenity API (requiere credenciales)."""
        from xerenity import Xerenity
        import os

        x_user = os.environ.get('XTY_USER', '')
        x_pass = os.environ.get('XTY_PWD', '')
        if not x_user or not x_pass:
            raise ValueError("Credenciales Xerenity no configuradas")

        x = Xerenity(x_user, x_pass)
        raw = x.series.search(ticker=TRM_XERENITY_TICKER)
        df = pd.DataFrame(raw).rename(columns={"time": "fecha", "value": "precio"})
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce")
        df = df[["fecha", "precio"]].dropna().sort_values("fecha")

        df = df[
            (df["fecha"] >= pd.to_datetime(start_date))
            & (df["fecha"] <= pd.to_datetime(end_date))
        ]

        result = pd.DataFrame({
            'date': df["fecha"].dt.strftime('%Y-%m-%d'),
            'close': df["precio"].values,
        })

        return result.reset_index(drop=True)


# ==================== IB UPDATER (on-demand) ====================

class IBUpdater:
    """
    Actualiza los archivos JSON de datos conectandose a Interactive Brokers.
    Basado en la logica de los notebooks (maiz.ipynb, azucar.ipynb, cacao.ipynb).

    Uso:
        updater = IBUpdater()
        await updater.update_all()
    """

    def __init__(self, host: str = IB_HOST, port: int = IB_PORT):
        self.host = host
        self.port = port

    async def update_commodity(self, asset_name: str,
                               client_id: int = 1) -> dict:
        """Actualiza datos de un commodity especifico via IB."""
        import asyncio
        from ib_async import IB, Future

        config = COMMODITY_CONFIG.get(asset_name)
        json_path = JSON_PATHS.get(asset_name)
        if not config or not json_path:
            return {'status': 'error', 'message': f'Asset {asset_name} no soportado'}

        db = _load_json(json_path)
        if not db:
            return {'status': 'error', 'message': f'JSON vacio: {json_path}'}

        ib = IB()
        try:
            await ib.connectAsync(self.host, self.port, clientId=client_id)
        except Exception as e:
            return {'status': 'error', 'message': f'No se pudo conectar a IB: {e}'}

        try:
            pattern = config['code_pattern']
            contracts = [k for k in db.keys() if re.fullmatch(pattern, k)]
            updated = 0

            for code in sorted(contracts):
                try:
                    yyyymm = _code_to_yyyymm(code, config)
                except ValueError:
                    continue

                # Qualify contract
                q = None
                for ex in config['exchanges']:
                    fut = Future(
                        symbol=config['symbol'],
                        lastTradeDateOrContractMonth=yyyymm,
                        exchange=ex,
                        currency="USD",
                        includeExpired=True,
                    )
                    try:
                        qs = await ib.qualifyContractsAsync(fut)
                        if qs:
                            q = qs[0]
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(0.05)

                if not q:
                    continue

                bars = db.get(code, [])
                last_date = max((r["date"] for r in bars), default=None)

                if last_date:
                    start = (pd.to_datetime(last_date) + timedelta(days=1)).strftime("%Y-%m-%d")
                    if start > datetime.now().strftime("%Y-%m-%d"):
                        continue

                    days = max(1, (datetime.now() - pd.to_datetime(start)).days + 1)
                    for what in ("TRADES", "BID_ASK", "MIDPOINT"):
                        try:
                            new_bars = await ib.reqHistoricalDataAsync(
                                q, endDateTime="",
                                durationStr=f"{days} D",
                                barSizeSetting="1 day",
                                whatToShow=what,
                                useRTH=False, formatDate=2,
                            )
                            if new_bars:
                                new_rows = [
                                    {
                                        "date": str(b.date), "open": b.open,
                                        "high": b.high, "low": b.low,
                                        "close": b.close, "volume": b.volume,
                                        "openinterest": None,
                                    }
                                    for b in new_bars if str(b.date) >= start
                                ]
                                if new_rows:
                                    merged = (
                                        pd.concat(
                                            [pd.DataFrame(bars), pd.DataFrame(new_rows)],
                                            ignore_index=True,
                                        )
                                        .drop_duplicates("date")
                                        .sort_values("date")
                                    )
                                    db[code] = merged.to_dict(orient="records")
                                    updated += 1
                                break
                        except Exception:
                            pass
                        await asyncio.sleep(0.25)

                await asyncio.sleep(0.5)

            # Guardar atomicamente
            if updated > 0:
                import os
                import tempfile
                json_path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(
                    prefix=json_path.name, dir=str(json_path.parent)
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(db, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, json_path)
                except Exception:
                    try:
                        os.remove(tmp)
                    finally:
                        raise

            return {'status': 'ok', 'updated': updated, 'asset': asset_name}

        finally:
            if ib.isConnected():
                ib.disconnect()

    async def update_all(self) -> dict:
        """Actualiza todos los commodities via IB."""
        results = {}
        client_id = 1
        for asset_name in COMMODITY_CONFIG:
            result = await self.update_commodity(asset_name, client_id=client_id)
            results[asset_name] = result
            client_id += 1
        return results


# ==================== REGISTRY ====================

COLLECTORS = {
    'MAIZ': CornCollector,
    'AZUCAR': SugarCollector,
    'CACAO': CocoaCollector,
    'USD': TRMCollector,
}


def collect_all(start_date: str, end_date: str) -> dict:
    """
    Ejecuta todos los collectors y retorna resumen.

    Returns:
        dict con conteo de registros por activo.
    """
    results = {}
    for name, CollectorClass in COLLECTORS.items():
        try:
            collector = CollectorClass()
            count = collector.collect_and_store(start_date, end_date)
            results[name] = {'status': 'ok', 'records': count}
        except Exception as e:
            results[name] = {'status': 'error', 'message': str(e)}
    return results


def fetch_all_prices(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Obtiene precios de todos los activos y los consolida en un DataFrame.
    Lee de archivos JSON (IB) para futuros y de Excel/Xerenity para TRM.

    Returns:
        DataFrame con columnas: ['date', 'MAIZ', 'AZUCAR', 'CACAO', 'USD']
    """
    all_data = {}

    for name, CollectorClass in COLLECTORS.items():
        try:
            collector = CollectorClass()
            df = collector.fetch_prices(start_date, end_date)
            if not df.empty:
                all_data[name] = df.set_index('date')['close']
        except Exception:
            continue

    if not all_data:
        return pd.DataFrame()

    result = pd.DataFrame(all_data)
    result.index.name = 'date'
    result = result.reset_index()
    result = result.sort_values('date').reset_index(drop=True)

    return result


def get_collectors_status() -> dict:
    """Retorna el estado de los datos disponibles por asset."""
    status = {}

    for name in ['MAIZ', 'AZUCAR', 'CACAO']:
        json_path = JSON_PATHS.get(name)
        if json_path and json_path.exists():
            db = _load_json(json_path)
            config = COMMODITY_CONFIG[name]
            front = _pick_front_contract(db, config)
            bars = db.get(front, [])
            last_date = max((r["date"] for r in bars), default="N/A") if bars else "N/A"
            n_contracts = len([
                k for k in db.keys()
                if re.fullmatch(config['code_pattern'], k)
            ])
            status[name] = {
                'source': 'IB/JSON',
                'json_file': str(json_path.name),
                'front_contract': front,
                'last_date': last_date,
                'total_contracts': n_contracts,
            }
        else:
            status[name] = {'source': 'N/A', 'error': 'JSON no encontrado'}

    # TRM
    if TRM_EXCEL_PATH.exists():
        try:
            df = pd.read_excel(TRM_EXCEL_PATH, sheet_name="sheet1")
            df.columns = [c.lower() for c in df.columns]
            df["fecha"] = pd.to_datetime(df["fecha"])
            last = df["fecha"].max().strftime('%Y-%m-%d')
            status['USD'] = {
                'source': 'Xerenity/Excel',
                'file': str(TRM_EXCEL_PATH.name),
                'last_date': last,
                'total_records': len(df),
            }
        except Exception as e:
            status['USD'] = {'source': 'Excel', 'error': str(e)}
    else:
        status['USD'] = {'source': 'N/A', 'error': 'Excel TRM no encontrado'}

    return status
