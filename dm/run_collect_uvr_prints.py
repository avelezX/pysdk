"""
UVR Projection Collector — calculates UVR projections and implicit inflation
directly (no HTTP roundtrip to the backend server).

Pipeline:
  1. Fetch inputs from Supabase: UVR history, TPM, TES bonds, CPI, COLTES grids
  2. Build TES COP and UVR yield curves → extract implicit inflation (breakeven)
  3. Project CPI index forward using implicit inflation
  4. Project UVR series forward: UVR_next = UVR_current × CPI_next / CPI_current
  5. Interpolate to daily frequency
  6. Store in: uvr_projection, inflacion_implicita tables

Runs daily via GitHub Actions (dm/.github/workflows/uvr_projection.yml)
"""
import sys
import os

# Add parent directory to path so we can import from the monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db_connection.supabase.Client import SupabaseConnection
import pandas as pd
import QuantLib as ql
from inflation_query.Inflation_query import InflacinImplicita
from utilities.date_functions import ql_to_datetime

# ── Configuration ──

BANREP_SERIES = {
    "TPM": 8,              # Tasa de Política Monetaria
    "UVR": 19,             # Unidad de Valor Real
}

# Bonds to exclude from curve building.
# These are either expired, illiquid, or cause fitting problems.
# Key: bond name as it appears in the `tes` table (lowercase).
EXCLUDED_BONDS_COP = ['tes_25']     # Expired or near-expiry COP bonds
EXCLUDED_BONDS_UVR = ['uvr_25']     # Expired or near-expiry UVR bonds


def fetch_inputs(connection):
    """Fetch all required data from Supabase."""

    print("[1/5] Fetching UVR historical data (serie 19)...")
    uvr_data = connection.read_table_limit(
        table_name='banrep_series_value_v2',
        limit=365 * 2,
        filter_by=('id_serie', BANREP_SERIES['UVR']),
        order_by='fecha',
        order_desc=True,
    )
    if not uvr_data:
        raise RuntimeError("No UVR historical data found in banrep_series_value_v2")
    print(f"       → {len(uvr_data)} rows")

    print("[2/5] Fetching TPM (Tasa de Política Monetaria)...")
    cbr_rows = connection.read_table_limit(
        table_name='banrep_series_value_v2',
        limit=1,
        filter_by=('id_serie', BANREP_SERIES['TPM']),
        order_by='fecha',
        order_desc=True,
    )
    if not cbr_rows:
        raise RuntimeError("No TPM data found")
    cbr = cbr_rows[0]['valor']
    print(f"       → TPM = {cbr}%")

    print("[3/5] Fetching TES bond master data...")
    tes_data = connection.read_table(table_name='tes')
    print(f"       → {len(tes_data)} bonds")

    print("[4/5] Fetching CPI data...")
    last_cpi_data = connection.rpc('cpi_index_change', {
        'lag_value': 12,
        'id_canasta_search': 1,
    })
    df_cpi = pd.DataFrame(last_cpi_data)
    df_cpi.rename(columns={'value': 'percentage_change'}, inplace=True)
    df_cpi = df_cpi.sort_index()
    last_cpi = df_cpi['percentage_change'].iloc[-1]
    print(f"       → CPI 12m change = {last_cpi}%")

    last_cpi_lag_data = connection.rpc('cpi_index_nochange', {
        'id_canasta_search': 1,
    })
    last_cpi_lag_df = pd.DataFrame(last_cpi_lag_data)
    last_cpi_lag_df.rename(columns={'value': 'cpi_index', 'time': 'fecha'}, inplace=True)

    print("[5/5] Fetching COLTES grids (COP + UVR)...")
    col_tes_cop = connection.rpc('get_tes_grid_raw', {'money': 'COLTES-COP'})
    col_tes_uvr = connection.rpc('get_tes_grid_raw', {'money': 'COLTES-UVR'})
    col_tes = col_tes_cop + col_tes_uvr
    print(f"       → {len(col_tes_cop)} COP + {len(col_tes_uvr)} UVR quotes")

    return {
        'uvr_data': uvr_data,
        'cbr': cbr,
        'tes_data': tes_data,
        'last_cpi': last_cpi,
        'inflation_lag_0': last_cpi_lag_df,
        'col_tes': col_tes,
    }


def calculate_uvr_projection(inputs):
    """
    Calculate UVR projections using InflacinImplicita directly.

    Returns:
        (uvr_projection_df, cpi_implicit_df)
    """
    print("\n[CALC] Building inflation model...")

    calc_date = ql.Date.todaysDate()

    inflation_model = InflacinImplicita(
        calc_date=calc_date,
        central_bank_rate=inputs['cbr'],
        tes_table=pd.DataFrame(inputs['tes_data']),
        inflation_lag_0=inputs['inflation_lag_0'],
        last_cpi=inputs['last_cpi'],
        fixed_rate_excluded_bonds=EXCLUDED_BONDS_COP,
        uvr_excluded_bonds=EXCLUDED_BONDS_UVR,
        col_tes=inputs['col_tes'],
        uvr=pd.DataFrame(inputs['uvr_data']),
    )

    # Step 1: Build TES curves and extract breakeven inflation
    print("       → Building TES COP and UVR curves...")
    print("       → Extracting implicit inflation (breakeven)...")

    # Step 2: Project CPI index forward
    print("       → Projecting CPI index...")
    cpi = inflation_model.create_cpi_index()

    # Step 3: Project UVR series
    print("       → Projecting UVR series (10 years)...")
    uvr_projec = inflation_model.calculo_serie_uvr(cpi_serie=cpi['total_cpi'])

    # Step 4: Interpolate to daily frequency
    print("       → Interpolating to daily frequency...")

    if 'fecha' in uvr_projec.columns:
        uvr_projec['fecha'] = pd.to_datetime(uvr_projec['fecha'])
        uvr_projec.set_index('fecha', inplace=True)

    uvr_projec['valor'] = pd.to_numeric(uvr_projec['valor'], errors='coerce')
    uvr_projec.dropna(subset=['valor'], inplace=True)

    if not isinstance(uvr_projec.index, pd.DatetimeIndex):
        uvr_projec.index = pd.to_datetime(uvr_projec.index)

    uvr_daily = uvr_projec.resample('D').asfreq()
    uvr_daily = uvr_daily.interpolate(method='linear')

    # Filter: only future dates
    today = pd.Timestamp.today().normalize()
    uvr_daily = uvr_daily[uvr_daily.index >= today]
    uvr_daily = uvr_daily.dropna()
    uvr_daily = uvr_daily.reset_index().rename(columns={'index': 'fecha'})
    uvr_daily['fecha'] = uvr_daily['fecha'].apply(str)

    print(f"       → {len(uvr_daily)} daily UVR values projected")

    # Step 5: CPI implicit (YoY inflation curve)
    cpi_total = cpi['total_cpi'].reset_index().rename(columns={'index': 'fecha'})
    cpi_total['fecha'] = pd.to_datetime(cpi_total['fecha'])
    cpi_total['indice'] = cpi_total['indice'].pct_change(periods=12) * 100
    cpi_total.dropna(inplace=True)
    cpi_filtered = cpi_total[cpi_total['fecha'] >= ql_to_datetime(calc_date)].copy()
    cpi_filtered['fecha'] = cpi_filtered['fecha'].apply(str)

    print(f"       → {len(cpi_filtered)} monthly inflation points")

    return uvr_daily, cpi_filtered


def store_results(connection, uvr_df, cpi_df):
    """Delete old data and insert new projections."""

    print("\n[STORE] Writing uvr_projection...")
    connection.delete_where_colum_is_not_null(
        table_name='uvr_projection', column_name='fecha'
    )
    connection.insert_dataframe(frame=uvr_df, table_name='uvr_projection')
    print(f"        → {len(uvr_df)} rows inserted")

    print("[STORE] Writing inflacion_implicita...")
    connection.delete_where_colum_is_not_null(
        table_name='inflacion_implicita', column_name='fecha'
    )
    connection.insert_dataframe(frame=cpi_df, table_name='inflacion_implicita')
    print(f"        → {len(cpi_df)} rows inserted")


def main():
    print("=" * 60)
    print("UVR Projection Collector")
    print("=" * 60)

    connection = SupabaseConnection()
    connection.sign_in_as_collector()

    try:
        inputs = fetch_inputs(connection)
        uvr_df, cpi_df = calculate_uvr_projection(inputs)
        store_results(connection, uvr_df, cpi_df)
        print("\n✓ UVR projection completed successfully")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
