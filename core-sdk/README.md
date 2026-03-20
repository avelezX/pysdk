<p align="center">
  <img src="logo.svg" alt="Xerenity" width="340"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/xerenity/"><img src="https://img.shields.io/pypi/v/xerenity?color=3b82f6&label=PyPI&logo=python&logoColor=white" alt="PyPI"/></a>
  <a href="https://pypi.org/project/xerenity/"><img src="https://img.shields.io/pypi/pyversions/xerenity?color=06b6d4&logo=python&logoColor=white" alt="Python"/></a>
  <img src="https://img.shields.io/badge/data-4600%2B%20series-8b949e" alt="Series"/>
  <img src="https://img.shields.io/badge/coverage-Colombia%20%26%20LatAm-8b949e" alt="Coverage"/>
  <img src="https://img.shields.io/badge/license-MIT-8b949e" alt="License"/>
</p>

<p align="center">
  Python SDK for <strong>Xerenity</strong> — a financial and economic data platform focused on Colombia and Latin America.<br/>
  Access 4,600+ time series across 25 groups: FIC funds (2,117 series), interest rates, exchange rates, inflation, TES bonds, US rates, Banrep macro, and more.
</p>

---

## Install

```bash
pip install xerenity
pip install xerenity pandas   # recommended — enables DataFrame output
```

## Authenticate

```python
from xerenity import Xerenity

x = Xerenity("your@email.com", "password")
# Register at https://xerenity.vercel.app
```

---

## API Reference

### `x.series` — Time Series

#### `x.series.groups() → list[str]`

Returns the live list of groups from the database (25 groups, 4,600+ series).

```python
x.series.groups()
# ['Agregados Crediticios', 'Agregados Monetarios', 'COLTES', 'Construccion',
#  'Cuentas Nacionales', 'Divisas', 'Empleo y Salarios', 'FIC', 'IBR-SWAP',
#  'Índices de Precios', 'Índices de Riesgo', 'Inflación', 'Peru Precios',
#  'Peru Tasas', 'Política Monetaria', 'Renta Fija', 'Sector Externo',
#  'Sector Fiscal', 'Sector Real', 'Tasa de Usura', 'Tasas de Captación',
#  'Tasas de Colocación', 'Tasas de Interés', 'Tasas Implícitas', 'Tasas USD']
```

---

#### `x.series.portfolio(...) → list[dict] | DataFrame`

Browse the full catalog with optional filters.

```python
x.series.portfolio(
    grupo: str = None,               # primary group — see groups()
    sub_group: str = None,           # secondary group within grupo
    fuente: str = None,              # data source: 'BanRep', 'DTCC', 'NY Fed', ...
    activo: bool = None,             # True = only series with data in the last 90 days
    frequency: str = None,           # 'D' | 'W' | 'M' | 'Q' | 'A' | 'I'
    es_compartimento: bool = None,   # (FIC only) True = FCP sub-compartments only
    apertura: str = None,            # (FIC only) 'Abierto' | 'Abierto con pacto' |
                                     #            'Abierto sin pacto' | 'Cerrado'
    as_dataframe: bool = False
) → list[dict] | pd.DataFrame
```

**Frequency codes:**

| Code | Meaning |
|------|---------|
| `D` | Daily |
| `W` | Weekly |
| `M` | Monthly |
| `Q` | Quarterly |
| `A` | Annual |
| `I` | Irregular (event-driven) |

**Return schema — each dict/row contains:**

| Field | Type | Description |
|-------|------|-------------|
| `source_name` | str | Human-readable slug — use this in `search(slug=...)` |
| `display_name` | str | Display name |
| `description` | str | Detailed description |
| `grupo` | str | Primary group |
| `sub_group` | str | Secondary group |
| `fuente` | str | Data source |
| `frequency` | str | Frequency code D/W/M/Q/A/I |
| `unit` | str | Unit of value (see unit reference below) |
| `entidad` | str\|None | Fund manager — only for FIC, null otherwise |
| `activo` | bool\|None | True if data exists within last 90 days |
| `es_compartimento` | bool\|None | True if FCP sub-compartment — only for FIC |
| `apertura` | str\|None | Fund structure: `Abierto`, `Abierto con pacto`, `Abierto sin pacto`, `Cerrado` — only for FIC |
| `ticker` | str | MD5 hash — legacy identifier |

**Unit reference:**

| Unit | Meaning |
|------|---------|
| `% EA` | Effective Annual Rate (Efectiva Anual) |
| `% NA` | Nominal Annual Rate (Nominal Anual) |
| `% NA/MV` | Nominal Annual, period compounding |
| `% Real` | Real yield (inflation-adjusted) |
| `%` | Percent, convention varies by source |
| `bps` | Basis points |
| `COP/USD` | Colombian pesos per US dollar |
| `COP/UVR` | Colombian pesos per UVR unit |
| `COP/unidad` | Pesos per fund unit (FIC) |
| `Índice` | Index number |
| `Índice 2018=100` | CPI index, base year 2018 |
| `Miles de MM COP` | Thousands of billions of COP |
| `MM COP` | Billions of COP |
| `MM USD` | Millions of USD |

**Examples:**

```python
# All series in a group
x.series.portfolio(grupo="IBR-SWAP")
x.series.portfolio(grupo="FIC")
x.series.portfolio(grupo="Tasas de Interés")

# Filter by sub-group
x.series.portfolio(grupo="Tasas de Interés", sub_group="IBR")
x.series.portfolio(grupo="FIC", sub_group="Fic del mercado monetario")

# Only active daily series
x.series.portfolio(activo=True, frequency="D")

# FIC filters — apertura and compartimentos
x.series.portfolio(grupo="FIC", apertura="Abierto con pacto")
x.series.portfolio(grupo="FIC", apertura="Cerrado")
x.series.portfolio(grupo="FIC", apertura="Abierto sin pacto")
x.series.portfolio(grupo="FIC", es_compartimento=True)   # FCP sub-compartments
x.series.portfolio(grupo="FIC", es_compartimento=False, activo=True)  # active principal funds

# As DataFrame (requires pandas)
df = x.series.portfolio(grupo="IBR-SWAP", as_dataframe=True)
df = x.series.portfolio(grupo="FIC", apertura="Abierto", as_dataframe=True)
```

---

#### `x.series.search_by_name(query: str) → list[dict]`

Search catalog by display name (case-insensitive).

```python
x.series.search_by_name("desempleo")
x.series.search_by_name("IBR")
x.series.search_by_name("SOFR")
x.series.search_by_name("usura")
```

Returns the same schema as `portfolio()`.

---

#### `x.series.entities(grupo: str = None) → list[str]`

Returns sorted list of unique entities (fund managers). Mainly useful for FIC.

```python
x.series.entities(grupo="FIC")
# ['Alianza Valores', 'Bancolombia', 'BTG Pactual', 'Davivienda', ...]

x.series.entities()   # all entities across all groups
```

---

#### `x.series.search(slug, ticker, desde, hasta) → list[dict]`

Download historical data for a single series.

```python
x.series.search(
    slug: str = None,    # source_name from portfolio() — RECOMMENDED
    ticker: str = None,  # MD5 hash from portfolio() — legacy
    desde: str = None,   # start date inclusive, 'YYYY-MM-DD'
    hasta: str = None,   # end date inclusive, 'YYYY-MM-DD'
) → list[dict]
```

**Return schema:**

```python
[
    {"time": "2024-01-02", "value": 10.587},
    {"time": "2024-01-03", "value": 10.590},
    ...
]
```

- `time`: always `"YYYY-MM-DD"` string
- `value`: float in the units specified by `unit` in portfolio()

**Examples:**

```python
# Recommended: use slug
x.series.search(slug="ibr_3m")
x.series.search(slug="USD:COP")
x.series.search(slug="SOFR")
x.series.search(slug="NOMINAL_120")      # UST 10Y
x.series.search(slug="sofr_swap_60")     # SOFR OIS 5Y

# With date filter
x.series.search(slug="ibr_3m", desde="2024-01-01", hasta="2024-12-31")
x.series.search(slug="USD:COP", desde="2023-01-01")

# Discovery → download workflow
catalog = x.series.portfolio(grupo="Política Monetaria")
data = x.series.search(slug=catalog[0]["source_name"])
```

**Key slugs by group:**

| Group | Example slugs |
|-------|--------------|
| IBR-SWAP | `ibr_1m`, `ibr_3m`, `ibr_6m`, `ibr_1y`, `ibr_2y`, `ibr_5y`, `ibr_10y` |
| Tasas Implícitas | `ibr_implicita_1m`, `ibr_implicita_3m`, `ibr_implicita_6m`, `ibr_implicita_12m` |
| Divisas | `USD:COP` (TRM), `cop_fwd_fx_1`, `cop_fwd_fx_3`, `cop_fwd_fx_6`, `cop_fwd_fx_12` |
| Tasas USD — Ref | `SOFR`, `EFFR`, `OBFR`, `SOFR_AVG_30D`, `SOFR_AVG_90D`, `SOFR_AVG_180D` |
| Tasas USD — UST | `NOMINAL_12` (1Y), `NOMINAL_60` (5Y), `NOMINAL_120` (10Y), `NOMINAL_360` (30Y) |
| Tasas USD — TIPS | `TIPS_60` (5Y), `TIPS_120` (10Y) |
| Tasas USD — SOFR Swap | `sofr_swap_1`, `sofr_swap_12`, `sofr_swap_60`, `sofr_swap_120` |
| COLTES | `tes_25`, `tes_30`, `uvr_29` |
| Índices de Riesgo | `Colombia`, `Brazil`, `Mexico`, `Peru` (EMBI) |
| Política Monetaria | via `portfolio(grupo="Política Monetaria")` |
| Banrep / SUAMECA | numeric string IDs via `portfolio(fuente="Banrep")` |

---

#### `x.series.search_multiple(slugs, desde, hasta) → pd.DataFrame`

Download N series simultaneously. Requires pandas.

```python
x.series.search_multiple(
    slugs: list[str],    # list of source_name slugs
    desde: str = None,   # start date inclusive, 'YYYY-MM-DD'
    hasta: str = None,   # end date inclusive, 'YYYY-MM-DD'
) → pd.DataFrame
```

**Return:** DataFrame with `datetime` index and one column per slug. `NaN` where no data for that date.

```python
# IBR curve
df = x.series.search_multiple(
    ["ibr_1m", "ibr_3m", "ibr_6m", "ibr_1y", "ibr_2y", "ibr_5y", "ibr_10y"]
)
#             ibr_1m  ibr_3m  ibr_6m  ibr_1y  ibr_2y  ibr_5y  ibr_10y
# 2026-03-01   9.759  10.587  11.408  12.419  12.045  11.680   11.275

# USD rates with date filter
df = x.series.search_multiple(
    ["SOFR", "EFFR", "NOMINAL_120", "sofr_swap_120"],
    desde="2024-01-01"
)

# FX + rates
df = x.series.search_multiple(["USD:COP", "ibr_3m", "SOFR"], desde="2023-01-01")
df.plot(subplots=True)
```

---

### `x.marks` — Daily Market Snapshots

Pre-computed daily snapshot of all key market curves and rates. One row per business day.

#### `x.marks.latest() → dict`

```python
snap = x.marks.latest()
```

#### `x.marks.snapshot(fecha: str) → dict | None`

```python
snap = x.marks.snapshot("2026-03-03")
```

**Return schema:**

```python
{
    "fecha":   "2026-03-03",      # str, ISO date
    "fx_spot": 4150.25,           # float, USD/COP spot (SET-ICAP)
    "sofr_on": 4.33,              # float, SOFR overnight %

    "ibr": {                      # IBR OIS curve (% NA), 8 nodes
        "ibr_1d":  9.636,
        "ibr_1m":  9.759,
        "ibr_3m":  10.587,
        "ibr_6m":  11.408,
        "ibr_12m": 12.419,
        "ibr_2y":  12.045,
        "ibr_5y":  11.680,
        "ibr_10y": 11.275
    },

    "sofr": {                     # SOFR zero rates (%), keyed by tenor_months
        "1":   3.661,
        "3":   3.655,
        "6":   3.594,
        "12":  3.428,
        "24":  3.251,
        "60":  3.286,
        "120": 3.591,
        "240": 3.978
    },

    "ndf": {                      # USD/COP NDF forwards, keyed by tenor_months
        "1":  {"fwd_pts_cop": 27.25,  "F_market": 3830.25, "deval_ea": 8.95},
        "3":  {"fwd_pts_cop": 83.75,  "F_market": 3886.75, "deval_ea": 9.10},
        "6":  {"fwd_pts_cop": 172.50, "F_market": 3975.50, "deval_ea": 9.28},
        "9":  {"fwd_pts_cop": 266.00, "F_market": 4069.00, "deval_ea": 9.43},
        "12": {"fwd_pts_cop": 363.00, "F_market": 4166.00, "deval_ea": 9.55}
    }
}
```

#### `x.marks.history(desde, hasta) → pd.DataFrame`

Historical snapshots as a DataFrame with expanded columns. Requires pandas.

```python
x.marks.history(
    desde: str = None,   # 'YYYY-MM-DD'
    hasta: str = None    # 'YYYY-MM-DD'
) → pd.DataFrame
```

**Columns:** `fx_spot`, `sofr_on`, `ibr_1d`, `ibr_1m`, `ibr_3m`, `ibr_6m`, `ibr_12m`, `ibr_2y`, `ibr_5y`, `ibr_10y`, `sofr_1`, `sofr_3`, `sofr_6`, `sofr_12`, `sofr_24`, `sofr_60`, `sofr_120`, `sofr_240`, `ndf_1_fwd_pts_cop`, `ndf_1_F_market`, `ndf_1_deval_ea`, ... (5 NDF tenors × 3 fields)

```python
df = x.marks.history(desde="2026-01-01")
df[["ibr_3m", "ibr_10y", "fx_spot"]].plot()

# Last IBR snapshot as Series
snap = x.marks.latest()
ibr = snap["ibr"]   # dict with ibr_1d … ibr_10y
```

---

### `x.loans` — Loan Portfolio

Manage and analyze cash flows for a credit portfolio.

```python
# List loans
x.loans.list_all()
x.loans.list_all(bank_names=["Bancolombia", "Davivienda"])

# Cash flow for one loan
x.loans.cash_flow(loan_id="<id>", filter_date="2026-01-01")

# Aggregated cash flow for multiple loans
x.loans.all_cash_flow(loan_list=["<id1>", "<id2>"], filter_date="2026-01-01")

# Create a loan
x.loans.create_loan(
    start_date="2026-01-01",
    bank="Bancolombia",
    number_of_payments=36,
    original_balance=1_000_000_000,   # COP
    periodicity="monthly",
    interest_rate=0.14,               # decimal, e.g. 0.14 = 14%
    type="IBR",
    days_count="ACT/365",
)
```

---

## Data Groups Reference

| Group | Sources | ~Series | Frequency | Unit |
|-------|---------|---------|-----------|------|
| `FIC` | Superintendencia Financiera (datos.gov.co) | 2,117 | D | COP/unidad |
| `Tasas de Colocación` | Banrep | 1,355 | M | % EA |
| `Sector Externo` | Banrep | 236 | M/Q | various |
| `Divisas` | SET-ICAP | 106 | D | COP/USD |
| `Índices de Precios` | Banrep / DANE / Camacol | 106 | M | Índice / % |
| `Sector Real` | Banrep / DANE | 84 | M/Q | various |
| `Política Monetaria` | Banrep | 78 | D/I/M | % EA |
| `Tasas de Interés` | Banrep | 62 | D/M | % EA |
| `Sector Fiscal` | Banrep / Minhacienda | 59 | M/Q/A | MM COP / % |
| `Agregados Monetarios` | Banrep | 52 | M | Miles de MM COP |
| `Tasas de Captación` | Banrep | 52 | W/M | % EA |
| `Tasas USD` | NY Fed / Treasury / Eris (CME) | 46 | D | % / % Real |
| `Agregados Crediticios` | Banrep | 36 | M | Miles de MM COP / % |
| `Construccion` | DANE / Camacol | 29 | M | Índice / Miles de MM COP |
| `IBR-SWAP` | DTCC | 24 | D | % NA |
| `Inflación` | DANE / Banrep | 24 | M | % |
| `COLTES` | BVC / SEN | 21 | D | % EA |
| `Índices de Riesgo` | J.P. Morgan | 17 | D | bps |
| `Renta Fija` | Banrep | 16 | D/M | % EA |
| `Peru Tasas` | BCRP | 15 | D/M | % EA |
| `Cuentas Nacionales` | Banrep / DANE | 4 | Q/A | Miles de MM COP |
| `Tasas Implícitas` | Xerenity (calculated) | 4 | D | % NA/MV |
| `Peru Precios` | BCRP / INEI | 2 | M | Índice |
| `Empleo y Salarios` | Banrep / DANE | 2 | M | % |
| `Tasa de Usura` | Superfinanciera | 1 | M | % EA |

---

## Typical Workflows

### Discover → Download

```python
# 1. Browse what's available
catalog = x.series.portfolio(grupo="IBR-SWAP", as_dataframe=True)
print(catalog[["source_name", "display_name", "frequency", "unit"]])

# 2. Download a series
data = x.series.search(slug="ibr_3m", desde="2024-01-01")

# 3. Convert to DataFrame
import pandas as pd
df = pd.DataFrame(data)
df["time"] = pd.to_datetime(df["time"])
df = df.set_index("time")
```

### Multi-Series Analysis

```python
# Download the full IBR OIS curve
ibr_curve = x.series.search_multiple(
    ["ibr_1m", "ibr_3m", "ibr_6m", "ibr_1y", "ibr_2y", "ibr_5y", "ibr_10y"],
    desde="2023-01-01"
)

# Compare Colombia vs US rates
rates = x.series.search_multiple(
    ["ibr_3m", "SOFR", "NOMINAL_120", "USD:COP"],
    desde="2024-01-01"
)
```

### Market Dashboard

```python
# Today's snapshot
snap = x.marks.latest()
print(f"TRM: {snap['fx_spot']}")
print(f"IBR 3M: {snap['ibr']['ibr_3m']}% NA")
print(f"SOFR ON: {snap['sofr_on']}%")

# 30-day history of key curves
df = x.marks.history(desde="2026-02-01")
df[["ibr_3m", "ibr_10y", "sofr_60", "fx_spot"]].plot(subplots=True, figsize=(12, 10))
```

### FIC Fund Explorer

FIC (Fondos de Inversión Colectiva) are Colombian collective investment funds supervised by the Superintendencia Financiera. The catalog contains **2,117 series** (965 active funds across 382 distinct funds).

**Fund types** (`sub_group`): `FIC De Tipo General`, `Fondos De Capital Privado`, `FIC De Mercado Monetario`, `FIC Inmobiliarias`, `FIC Bursatiles`.

**Fund structure** (`apertura`):

| Value | Description | # series |
|-------|-------------|----------|
| `Abierto` | Open-end, no lock-in | 392 |
| `Abierto con pacto` | Open-end with lock-in period | 289 |
| `Abierto sin pacto` | Open-end, explicitly no lock-in | 89 |
| `Cerrado` | Closed-end | 259 |
| `None` | FCP compartments / MM / unlabeled | 1,088 |

**Compartments** (`es_compartimento`): Private equity funds (FCP) can have multiple compartments, each with its own `codigo_negocio`. Use `es_compartimento=True` to filter only compartments, `False` for principal/standalone funds.

```python
# All fund managers
managers = x.series.entities(grupo="FIC")

# Browse by fund type
x.series.portfolio(grupo="FIC", sub_group="FIC De Mercado Monetario")
x.series.portfolio(grupo="FIC", sub_group="Fondos De Capital Privado")

# Browse by structure
x.series.portfolio(grupo="FIC", apertura="Abierto con pacto")
x.series.portfolio(grupo="FIC", apertura="Cerrado")

# Active principal funds only (excludes FCP sub-compartments)
funds = x.series.portfolio(
    grupo="FIC", es_compartimento=False, activo=True, as_dataframe=True
)

# FCP sub-compartments
compartments = x.series.portfolio(grupo="FIC", es_compartimento=True, as_dataframe=True)

# Download NAV history for a specific fund
fund_slug = funds.iloc[0]["source_name"]
nav = x.series.search(slug=fund_slug, desde="2023-01-01")

# Compare two funds
df = x.series.search_multiple(
    [funds.iloc[0]["source_name"], funds.iloc[1]["source_name"]],
    desde="2024-01-01"
)
```

---

## For AI Agents

> This section provides structured context for LLM agents consuming this API.

**Discovery pattern:** Always call `portfolio()` first to get the `source_name` (slug), then pass it to `search(slug=...)`. Never guess slugs except for the key ones listed in the slug reference table above.

**Data shape invariant:** `search()` always returns `list[{"time": "YYYY-MM-DD", "value": float}]` sorted ascending by date. `time` is always a string, never a datetime object. Values are in the units specified by `unit` in the catalog.

**Scale:** IBR-SWAP rates are stored as `%` (e.g., `10.587` = 10.587% NA), not as decimals. Same for UST, SOFR, EFFR. EMBI is in basis points (e.g., `185` = 185 bps). Exchange rates are COP per USD (e.g., `4150.25`).

**Pandas dependency:** `search_multiple()`, `portfolio(as_dataframe=True)`, and `marks.history()` require pandas. Check if available before calling.

**No data case:** If a series has no data for the requested date range, `search()` returns an empty list `[]`. `marks.snapshot()` returns `None` if the date doesn't exist.

**Rate convention summary:**
- Colombian rates (IBR OIS, COLTES, DTF): Effective Annual `% EA` unless stated `% NA`
- US overnight rates (SOFR, EFFR, OBFR): simple annualized `%`, Act/360
- US swap rates (SOFR OIS): par coupon `%`, Act/360
- US Treasury yields: Bond-Equivalent Yield `%`, Act/Act semiannual
- EMBI: spread over US Treasuries, in basis points

**Authentication:** credentials are per-session. The `Xerenity()` constructor calls login immediately. There is no token refresh — instantiate once per script/session.
