# Glosario de Series — Xerenity

Xerenity agrupa más de 1.000 series de tiempo financieras y económicas en **13 grupos** jerárquicos.
Cada serie tiene los siguientes campos:

| Campo | Descripción |
|-------|-------------|
| `ticker` | Identificador único para usar en `search(ticker)` |
| `display_name` | Nombre legible de la serie |
| `description` | Descripción detallada |
| `grupo` | Clasificación primaria (ver tabla abajo) |
| `sub_group` | Clasificación secundaria dentro del grupo |
| `fuente` | Fuente/origen del dato |
| `entidad` | Entidad gestora (aplica solo para FIC) |
| `activo` | `True` si tiene datos en los últimos 90 días |

---

## Cómo explorar el catálogo desde Python

```python
from xerenity import Xerenity

x = Xerenity(username, password)

# Ver todos los grupos disponibles
x.series.groups()
# → ['COLTES', 'Cuentas Nacionales', 'Divisas', ...]

# Ver todo el catálogo
x.series.portfolio()

# Filtrar por grupo
x.series.portfolio(grupo="IBR-SWAP")

# Filtrar por grupo y sub_group
x.series.portfolio(grupo="Tasas de Interés", sub_group="IBR")

# Solo series activas (con datos recientes)
x.series.portfolio(activo=True)

# Buscar por nombre
x.series.search_by_name("desempleo")

# Obtener los datos de una serie
x.series.search(ticker="<ticker>")
```

---

## Los 13 Grupos

---

### 1. COLTES — Bonos del Gobierno Colombiano (TES)

Tasas de rendimiento de los TES (Títulos de Tesorería) del gobierno colombiano, tanto en pesos (COP) como en UVR (inflación-indexados).

**Fuente:** Bolsa de Valores de Colombia (BVC) / SEN
**Frecuencia:** Diaria (días hábiles)
**Unidad:** % Efectivo Anual

| Sub grupo | Descripción | Ejemplo de serie |
|-----------|-------------|-----------------|
| TES COP | Bonos tasa fija en pesos | TES vencimiento 2026, 2028, 2030... 2050 |
| TES UVR | Bonos indexados a inflación (UVR) | UVR vencimiento 2025, 2027... 2049 |
| TES Variable | Bonos tasa variable | TESV 2031 |

**Ejemplo de uso:**
```python
tes = x.series.portfolio(grupo="COLTES")
# Cada serie: ISIN, cupón, fecha de vencimiento, yield diario
```

---

### 2. Cuentas Nacionales — PIB y Actividad Económica

Indicadores de la actividad económica agregada de Colombia: PIB y sus componentes por oferta y demanda, incluyendo el sector construcción.

**Fuentes:** Banco de la República (Banrep), DANE, CAMACOL
**Frecuencia:** Trimestral / Mensual (según la serie)
**Unidad:** Miles de millones de COP (precios constantes 2015), variaciones %

| Sub grupo | Descripción | Ejemplos |
|-----------|-------------|---------|
| PIB Oferta | PIB por sector productivo | Total, Construcción, Actividades especializadas |
| PIB Demanda | PIB por componente de gasto | Consumo Final, Formación Bruta de Capital |
| PIB Construcción | Detalle sector constructor | Edificaciones, Obras Civiles |
| Cemento | Producción y despachos de cemento | Producción mensual, variación anual |
| Financiación | Créditos constructor y adquisición | VIS/No-VIS, COP/UVR |

**Ejemplo de uso:**
```python
pib = x.series.portfolio(grupo="Cuentas Nacionales", sub_group="PIB Demanda")
```

---

### 3. Divisas — Tasas de Cambio y Criptomonedas

Tipos de cambio spot, forwards y precios de criptomonedas.

**Fuentes:** SET-ICAP / Banrep (TRM), FXEmpire (forwards), CryptoCompare (crypto), BCE (cruces)
**Frecuencia:** Diaria / Intradiaria
**Unidad:** COP por USD, puntos forward, USD por unidad cripto

| Sub grupo | Descripción | Ejemplos |
|-----------|-------------|---------|
| TRM / Spot | Tasa Representativa del Mercado USD/COP | TRM oficial diaria |
| Forwards NDF | Puntos forward USD/COP | SN, 1M, 2M, 3M, 6M, 9M, 1Y |
| Cruces | Pares de monedas internacionales | EUR/USD, otras |
| Crypto | Precios de criptomonedas en USD | BTC, ETH, SOL, XRP, ADA, DOGE, AVAX, BNB, DOT, MATIC, LINK, LTC, UNI, ATOM, NEAR, APT, ARB, OP, FTM, ALGO |

**Ejemplo de uso:**
```python
fx = x.series.portfolio(grupo="Divisas", sub_group="Forwards NDF")
crypto = x.series.portfolio(grupo="Divisas", sub_group="Crypto")
```

---

### 4. Empleo y Salarios — Mercado Laboral

Indicadores del mercado laboral colombiano: tasas de empleo y desempleo a nivel nacional.

**Fuentes:** Banco de la República, DANE
**Frecuencia:** Mensual
**Unidad:** % de la población en edad de trabajar

| Sub grupo | Descripción |
|-----------|-------------|
| Desempleo | Tasa de desempleo nacional |
| Empleo | Tasa de empleo / ocupación |

**Ejemplo de uso:**
```python
empleo = x.series.portfolio(grupo="Empleo y Salarios")
desempleo = x.series.search_by_name("desempleo")
```

---

### 5. FIC — Fondos de Inversión Colectiva

Valor de la unidad (NAV) y activos bajo administración de los Fondos de Inversión Colectiva colombianos. Más de 200 fondos de distintas gestoras.

**Fuente:** Superintendencia Financiera de Colombia
**Frecuencia:** Diaria
**Unidad:** COP por unidad (valor unidad), COP total (AUM)

| Sub grupo (tipo de fondo) | Descripción |
|--------------------------|-------------|
| Fic de tipo general | Fondos de renta variable y mixtos |
| Fic bursatiles | Fondos que replican índices bursátiles |
| Fic del mercado monetario | Fondos de liquidez (money market) |
| Fic inmobiliarias | Fondos de inversión en bienes raíces |
| Fondos de capital privado | Private equity y deuda privada |

**Entidades (gestoras) disponibles:** Credicorp Capital, BTG Pactual, Valores Bancolombia, Fiduciaria Colmena, Global Securities, Progresión, y más de 20 gestoras adicionales.

**Ejemplo de uso:**
```python
# Por tipo de fondo
monetarios = x.series.portfolio(grupo="FIC", sub_group="Fic del mercado monetario")

# Por gestora
btg = x.series.portfolio(grupo="FIC", fuente="BTG Pactual")
```

---

### 6. IBR-SWAP — Curva OIS IBR

Tasas par de swaps OIS (Overnight Index Swap) indexados al IBR, provenientes de operaciones registradas en DTCC. Representan el costo de intercambiar tasa fija por IBR flotante a distintos plazos.

**Fuente:** DTCC (repositorio de derivados OTC)
**Frecuencia:** Diaria
**Unidad:** % Efectivo Anual (tasa par)

| Sub grupo | Tenores disponibles |
|-----------|-------------------|
| Curva OIS IBR | 1M, 2M, 3M, 4M, 6M, 9M, 1Y, 18M, 2Y, 3Y, 4Y, 5Y, 7Y, 10Y |

**Ejemplo de uso:**
```python
ibr_swaps = x.series.portfolio(grupo="IBR-SWAP")
# Útil para construir la curva IBR OIS o calcular tasas forward implícitas
```

---

### 7. Índices de Precios — Inflación y Precios

Índices de precios al consumidor (IPC), al productor (IPP), de vivienda (IPVN, IPVU) e inflación implícita. Incluye desagregación por ciudad y división de gasto.

**Fuentes:** Banco de la República, DANE, CAMACOL
**Frecuencia:** Mensual
**Unidad:** Índice base 2018 = 100, variaciones % mensual/anual

| Sub grupo | Descripción | Cobertura |
|-----------|-------------|-----------|
| IPC Nacional | Índice de precios al consumidor | Nivel nacional |
| IPC por Ciudad | IPC desagregado por ciudad | 22 ciudades: Bogotá, Medellín, Cali, Barranquilla, Bucaramanga, Cartagena, Cúcuta, Manizales, Pereira, y 13 más |
| IPC por División | IPC por categoría de gasto | Alimentos, vivienda, transporte, educación, salud... |
| IPP | Índice de precios al productor | Nacional |
| IPVN | Índice de precios de vivienda nueva | Nacional (Banrep) |
| IPVU | Índice de precios de vivienda usada | Nacional |
| ICOCED | Índice de costos de construcción | Mensual desde 2022 |
| Inflación Core | Inflación básica (sin volátiles) | 24 variantes metodológicas |

**Ejemplo de uso:**
```python
ipc = x.series.portfolio(grupo="Índices de Precios", sub_group="IPC Nacional")
ipc_bogota = x.series.search_by_name("IPC Bogotá")
```

---

### 8. Índices de Riesgo — Spreads y Riesgo País

Indicadores de riesgo soberano y de crédito de Colombia y la región.

**Fuente:** Alphacast (datos EMBI de JP Morgan)
**Frecuencia:** Diaria
**Unidad:** Puntos básicos (bps)

| Sub grupo | Descripción |
|-----------|-------------|
| EMBI | Emerging Markets Bond Index — spread soberano Colombia sobre UST |

**Ejemplo de uso:**
```python
riesgo = x.series.portfolio(grupo="Índices de Riesgo")
```

---

### 9. Política Monetaria — Banco de la República

Decisiones de política monetaria del Banco de la República de Colombia: tasa de intervención y meta de inflación.

**Fuente:** Banco de la República
**Frecuencia:** Por reunión de junta directiva (~8 veces al año)
**Unidad:** % Efectivo Anual

| Sub grupo | Descripción |
|-----------|-------------|
| Tasa de Política | Tasa de política monetaria (TPM) — tasa repo overnight del Banrep |
| Meta de Inflación | Meta de inflación del Banrep |

**Ejemplo de uso:**
```python
tpm = x.series.search_by_name("política monetaria")
```

---

### 10. Tasa de Usura — Límite Legal de Tasas

La tasa de usura es el límite máximo legal para el cobro de intereses en Colombia, definida por la Superintendencia Financiera. Se actualiza periódicamente por tipo de crédito.

**Fuente:** Superintendencia Financiera de Colombia
**Frecuencia:** Mensual / Periódica
**Unidad:** % Efectivo Anual

| Sub grupo | Descripción |
|-----------|-------------|
| Usura consumo | Crédito de consumo y ordinario |
| Usura microcrédito | Crédito microempresarial |

**Ejemplo de uso:**
```python
usura = x.series.portfolio(grupo="Tasa de Usura")
```

---

### 11. Tasas de Captación — Tasas de Depósito

Tasas de interés de captación de los establecimientos de crédito colombianos: DTF y CDT a distintos plazos.

**Fuente:** Banco de la República
**Frecuencia:** Semanal / Mensual
**Unidad:** % Nominal Anual / % Efectivo Anual

| Sub grupo | Descripción |
|-----------|-------------|
| DTF | Depósito a Término Fijo 90 días — promedio ponderado semanal y mensual |
| CDT 180d | Certificado de Depósito a Término 180 días |
| CDT 360d | Certificado de Depósito a Término 360 días |

**Contexto:** El DTF fue la tasa de referencia dominante en Colombia antes de la adopción del IBR. Sigue siendo ampliamente usada en contratos de crédito legacy.

**Ejemplo de uso:**
```python
dtf = x.series.search_by_name("DTF")
captacion = x.series.portfolio(grupo="Tasas de Captación")
```

---

### 12. Tasas de Interés — Tasas de Referencia

El grupo más amplio: tasas de referencia colombianas, estadounidenses y peruanas. Incluye la curva IBR, tasas SOFR, curvas del Tesoro de EE.UU. y tasas del Banco Central del Perú.

**Fuentes:** Banrep, NY Federal Reserve, US Treasury, Eris/CME, BCRP
**Frecuencia:** Diaria
**Unidad:** % Efectivo Anual / % Nominal

#### Colombia — IBR (Indicador Bancario de Referencia)
La tasa de referencia overnight del mercado interbancario colombiano, calculada por el Banrep. Es la base para swaps, derivados y créditos de tasa variable en COP.

| Tenor | Descripción |
|-------|-------------|
| IBR Overnight | Tasa overnight (nominal y efectiva) |
| IBR 1 Mes | Tasa a 1 mes (nominal y efectiva) |
| IBR 3 Meses | Tasa a 3 meses (nominal y efectiva) |
| IBR 6 Meses | Tasa a 6 meses (nominal y efectiva) |
| IBR 12 Meses | Tasa a 12 meses (nominal y efectiva) |

#### Colombia — UVR
Unidad de Valor Real: unidad de cuenta indexada al IPC, usada para denominar créditos hipotecarios y bonos TES UVR.

#### Colombia — Tasas de Colocación
Tasas activas del sistema financiero colombiano por modalidad de crédito (constructores, adquisición, consumo, comercial, microcrédito).

#### Estados Unidos — Tasas de Referencia (Fed / NY Fed)
| Serie | Descripción |
|-------|-------------|
| SOFR | Secured Overnight Financing Rate — tasa repo overnight en USD |
| EFFR | Effective Federal Funds Rate — tasa fondos federales efectiva |
| OBFR | Overnight Bank Funding Rate |
| SOFR 30D | Promedio SOFR 30 días |
| SOFR 90D | Promedio SOFR 90 días |
| SOFR 180D | Promedio SOFR 180 días |

#### Estados Unidos — Curva del Tesoro (UST)
Tasas de rendimiento de los bonos del Tesoro de EE.UU. a madurez constante.

| Curva | Tenores |
|-------|---------|
| UST Nominal | 1M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y |
| UST TIPS | 5Y, 7Y, 10Y, 20Y, 30Y (tasas reales) |

#### Estados Unidos — Curva SOFR OIS Swap
Tasas par de swaps OIS indexados a SOFR (futuros Eris/CME). Referencia clave para derivados en USD.

| Tenores disponibles |
|--------------------|
| 1M, 2M, 3M, 6M, 9M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 15Y, 20Y, 25Y, 30Y, 40Y, 50Y |

#### Perú — BCRP
Tasas del Banco Central de Reserva del Perú.

| Serie | Descripción |
|-------|-------------|
| Tasa Interbancaria PEN | Tasa overnight interbancaria en soles |
| Tasa de Política | Tasa de referencia del BCRP |
| TAMN / TAMEX | Tasas activas en soles / dólares |
| TIPMN / TIPMEX | Tasas pasivas en soles / dólares |
| Bono gobierno PEN/USD 10Y | Rendimiento soberano peruano |

**Ejemplo de uso:**
```python
ibr = x.series.portfolio(grupo="Tasas de Interés", sub_group="IBR")
ust = x.series.portfolio(grupo="Tasas de Interés", sub_group="UST Nominal")
sofr = x.series.search_by_name("SOFR")
```

---

### 13. Tasas Implícitas — Inflación Implícita del Mercado

Tasas de inflación implícitas derivadas de la diferencia de rendimiento entre los TES en COP (tasa fija) y los TES en UVR (indexados a inflación). Refleja las expectativas de inflación del mercado para distintos horizontes.

**Fuente:** Cálculo interno (TES COP vs TES UVR — Banrep/BVC)
**Frecuencia:** Diaria
**Unidad:** % Efectivo Anual

| Sub grupo | Descripción |
|-----------|-------------|
| Inflación implícita | Breakeven inflation por plazo (2Y, 5Y, 10Y, ...) |

**Ejemplo de uso:**
```python
impl = x.series.portfolio(grupo="Tasas Implícitas")
# Útil para comparar expectativas de mercado vs meta del Banrep
```

---

## Resumen rápido

| Grupo | Fuente principal | Series aprox. | Frecuencia |
|-------|-----------------|---------------|------------|
| COLTES | BVC / SEN | ~30 bonos activos | Diaria |
| Cuentas Nacionales | Banrep / DANE / CAMACOL | ~50 | Trimestral / Mensual |
| Divisas | SET-ICAP / FXEmpire / CryptoCompare | ~30 | Diaria |
| Empleo y Salarios | Banrep / DANE | ~5 | Mensual |
| FIC | Superintendencia Financiera | **200+** | Diaria |
| IBR-SWAP | DTCC | ~14 tenores | Diaria |
| Índices de Precios | Banrep / DANE / CAMACOL | ~80 | Mensual |
| Índices de Riesgo | Alphacast (EMBI) | ~5 | Diaria |
| Política Monetaria | Banrep | ~2 | Por reunión JDBR |
| Tasa de Usura | Superfinanciera | ~5 | Mensual |
| Tasas de Captación | Banrep | ~5 | Semanal |
| Tasas de Interés | Banrep / NY Fed / Treasury / BCRP | **600+** | Diaria |
| Tasas Implícitas | Cálculo interno | ~10 | Diaria |

**Total: más de 1.000 series activas**
