# Gestión de Riesgos - Module Guide

## Propósito
Sistema de gestión de riesgo de commodities para Super de Alimentos. Calcula VaR paramétrico, exposición USD, y consolida portafolio de cobertura (benchmark vs. gestión de riesgo).

## Arquitectura

```
gestion_de_riesgos/
├── db_risk.py              # Capa de datos — Supabase REST API
├── exposure.py             # Cálculo de exposición USD por commodity
├── portfolio.py            # Portafolio consolidado: posiciones + VaR + P&L
├── futures_portfolio.py    # Portafolio de futuros GR: P&L por posición individual
├── collectors/
│   ├── base_collector.py   # Framework de collectors (IB JSON, TRM Excel)
│   └── ibkr/               # Notebooks IB + datos históricos CSV
├── var_engine/
│   └── var_calculator.py   # Motor VaR paramétrico (rolling 180d, 99%)
└── sql/
    └── risk_futures_portfolio.sql  # DDL para tabla de posiciones de futuros
```

### Flujo de datos
```
IB Notebooks → JSON files → collectors → Supabase (risk_prices)
                                              ↓
                              db_risk.get_risk_prices()
                                              ↓
                                    var_engine (VaR factors)
                                              ↓
                                portfolio (risk_table consolidada)
```

## Módulos

### db_risk.py
Capa de acceso a Supabase via REST. Cuatro tablas:
- `risk_prices` — precios históricos de futuros (MAIZ, AZUCAR, CACAO, USD)
- `risk_positions` — posiciones benchmark y GR por activo (agregadas)
- `risk_portfolio_config` — configuración de portafolio (fechas, ventana rolling)
- `risk_futures_portfolio` — posiciones individuales de futuros (LONG/SHORT, roll tracking)

Env vars requeridas: `XTY_URL`, `XTY_TOKEN`, `COLLECTOR_BEARER` (opcional)

### collectors/base_collector.py (~760 líneas)
- `BaseCollector(ABC)` — interfaz para todos los collectors
- `FuturesJSONCollector` — lee JSON de IB, maneja lógica de roll de contratos
- Collectors específicos: `CornCollector`, `SugarCollector`, `CocoaCollector`
- `TRMCollector` — tasa USD/COP desde Excel o Xerenity API
- `IBUpdater` — actualización on-demand via ib_async (TWS)
- Funciones clave: `collect_all()`, `fetch_all_prices()`, `get_collectors_status()`

**Datos locales** (rutas hardcodeadas Windows):
- `DATA_DIR`: directorio SharePoint de Saman con JSONs de IB
- `JSON_PATHS`: `data_zc1.json` (maíz), `data_sb.json` (azúcar), `data_cc.json` (cacao)
- `trm.xlsx`: archivo Excel con TRM histórica

**Config de contratos (COMMODITY_CONFIG)**:
| Asset   | Ticker | Meses      | Expiry day | Roll days |
|---------|--------|------------|------------|-----------|
| MAIZ    | ZC     | H,K,N,U,Z | 14         | 10        |
| AZUCAR  | SB     | H,K,N,V   | 28 (mes-1) | 10        |
| CACAO   | CC     | H,K,N,U,Z | 14         | 10        |

### var_engine/var_calculator.py
VaR paramétrico (varianza-covarianza):
- Retornos logarítmicos
- Volatilidad rolling 180 días (min 30 observaciones)
- Z-score al 99% (configurable)
- Output: factores VaR diarios por activo, VaR en $ por posición

### exposure.py
Modela exposición de Super de Alimentos en USD:
- `AzucarExposure` — azúcar crudo ICE SB (112,000 lbs/contrato)
- `MaizGlucosaExposure` — maíz→glucosa CME ZC (con flete, processing, crédito subproductos)
- `CocoaDerivadoExposure` — 3 derivados (polvo 1.22x, manteca 1.95x, licor 1.53x)
- `EmpaqueExposure` — empaque (precio fijo, conversión via TRM)
- `calcular_exposicion_total()` — consolidación total + exposición neta USD

### portfolio.py
`RiskPortfolio` — consolida benchmark vs. GR:
- Posiciones por activo (benchmark, GR, total)
- VaR por tipo de posición
- P&L (precio inicio vs. fin de periodo)
- Information Ratio (P&L GR / VaR GR)
- Output: `build_risk_table()` → lista de dicts lista para API

### futures_portfolio.py
`FuturesPortfolioCalculator` — P&L por posición individual de futuros:
- Soporta LONG y SHORT (cuentas de margen)
- Multiplicadores por contrato: MAIZ=5,000 bu, AZUCAR=112,000 lbs, CACAO=10 ton
- **Precio Compra**: siempre fijo (entry_price)
- **Precio Previo**: si la posición se abrió en el mes seleccionado → entry_price;
  si lleva más de 1 mes → último día hábil del mes anterior (misma lógica que benchmark)
- **Precio Actual**: último precio disponible en Supabase
- **Valor T** = nominal x multiplicador x precio actual
- **Valor T-1** = nominal x multiplicador x precio previo
- **P&L Mes** = (precio actual - precio previo) x nominal x mult x dirección
- **P&L Inicio** = (precio actual - precio compra) x nominal x mult x dirección
- Roll de contratos: cierra posición vieja → abre nueva con `rolled_to` link
- Navegación por mes (misma lógica que benchmark): el filter_date se calcula como último día hábil del mes seleccionado

### sql/risk_futures_portfolio.sql
DDL para crear la tabla `risk_futures_portfolio` en Supabase:
- Campos: asset, contract, direction, nominal, entry_price, entry_date, active
- Campos de cierre: closed_date, closed_price, rolled_to
- Unique constraint: (asset, contract, entry_date, direction) para upsert

## API (Django Server)
Expuesto en `server/risk_management_server/risk_management_server.py` como `RiskManagementServer`:

| Método              | Descripción                                    |
|---------------------|------------------------------------------------|
| `calculate()`       | Tabla de riesgo completa (posiciones + VaR + P&L) |
| `benchmark_factors()` | Factores VaR, precios, covarianza, correlación |
| `rolling_var()`     | Serie histórica de precios y VaR rolling        |
| `collectors_status()` | Estado de collectors + calendario de contratos |
| `update_prices()`   | Actualiza precios en Supabase desde JSONs locales |
| `exposure()`        | Cálculo de exposición USD con precios de mercado |
| `futures_portfolio()` | Portafolio de futuros con P&L calculado |
| `futures_portfolio_upsert()` | Crear/actualizar posiciones de futuros |
| `futures_portfolio_roll()` | Ejecutar roll de contrato (cierra + abre) |
| `futures_portfolio_close()` | Cerrar una posición de futuros |
| `futures_portfolio_delete()` | Eliminar una posición de futuros |
| `futures_portfolio_edit()` | Editar campos de una posición existente |

Request mínimo: `{"filter_date": "2026-03-25"}`. Soporta `mock: true` para datos de prueba.

## Convenciones
- Posiciones negativas = compra de commodity (exposición corta/natural del negocio)
- Posiciones GR positivas en USD = cobertura vendida (forwards)
- Precios en unidades nativas del contrato (cents/lb para azúcar, cents/bu para maíz, USD/ton para cacao, COP/USD para TRM)
- VaR siempre en valor absoluto, expresado en las mismas unidades de la posición
- Factores VaR en porcentaje (e.g., 2.55% diario)

## Dependencias
```
pandas, numpy, scipy (norm)
requests (Supabase REST)
ib_async (Interactive Brokers TWS — solo IBUpdater)
```

## Notas y deuda técnica
- Rutas de datos hardcodeadas a directorio local de Windows/SharePoint — no funciona en deploy
- `__init__.py` vacíos en todos los subpaquetes (no hay re-exports)
- base_collector.py es el archivo más grande (~760 líneas) — candidato a split
- Los notebooks de ibkr/ generan los JSON que leen los collectors (dependencia implícita)
- La lógica de `benchmark_factors()` en el server es extensa y podría extraerse al módulo
