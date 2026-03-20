# Xerenity DM - Data Management - Claude Agent Workflow

## Qué es
Sistema de recolección y almacenamiento de datos financieros para la plataforma Xerenity. Conecta con múltiples fuentes de datos (Banco de la República, BIS, ECB, DANE, Camacol, DTCC, BCRP) y los almacena en la base de datos.

## Project Info
- **GitHub Org:** avelezX
- **Repo:** xerenity-dm
- **GitHub Project:** Xerenity (#4)
- **Tech:** Python 3, Docker, PostgreSQL

## Estructura
- `/data_collectors` - Módulos de recolección por fuente
- `/collect_and_store` - Lógica de almacenamiento
- `/db_connection` - Conexión a base de datos
- `/financial_variables` - Variables financieras calculadas
- `/functions_DM` - Funciones utilitarias
- `/data` - Datos temporales
- `run_collect_*.py` - Scripts de recolección individuales

## Scripts principales
| Script | Fuente |
|--------|--------|
| `run_collect_banrep_api.py` | Banco de la República API |
| `run_collect_trm.py` | TRM (tasa representativa) |
| `run_collect_us_rates.py` | Tasas US Treasury |
| `run_collect_ibr_swaps.py` | Swaps IBR |
| `run_collect_sofr_swaps.py` | Swaps SOFR |
| `run_collect_fx_ndf.py` | NDF FX forwards |
| `run_collect_fwd_rates.py` | Forward rates |
| `run_collect_camacol.py` | Datos Camacol |
| `run_collect_dane.py` | Datos DANE |
| `run_health_check.py` | Health check del sistema |

## Comandos
```bash
pip install -r requirements.txt
python run_collect_trm.py
docker build -t xerenity-dm .
```

## Reglas
- Siempre referenciar una issue en commits: `closes #X`
- No pushear directo a main, usar PRs
- Variables de conexión a DB van en variables de entorno

## Session Startup Protocol

**Al inicio de cada sesion, SIEMPRE ejecutar estos pasos antes de cualquier otra cosa:**

1. **Consultar GitHub Projects** - Listar las tareas pendientes del proyecto Xerenity:
   ```bash
   export PATH="$PATH:/c/Program Files/GitHub CLI"
   gh project item-list 4 --owner avelezX --format json
   ```

2. **Mostrar resumen al usuario** - Presentar tabla con:
   - Status (Todo, In Progress, Done)
   - Titulo
   - Repo asociado (filtrar las relevantes a este repo: xerenity-dm)
   - Prioridad si la tiene
   Filtrar y mostrar primero las tareas "In Progress" y "Todo".

3. **Preguntar cual tarea trabajar** - Si el usuario no especifica, preguntar cual tarea del backlog quiere abordar.

## Repos del ecosistema Xerenity
- **xerenity-fe** - Frontend (React/TypeScript)
- **xerenity-dm** - Data management / collectors (este repo)
- **xerenity-db** - Migraciones y esquema DB (SQL/Supabase)
- **xerenity-api** - API
- **pysdk** - Python SDK / pricing backend
- **XerenityAddin** - Excel Addin (C#)
- **xerenity-explorer** - Explorador de datos (Python/Jupyter)
- **ui-components** - Libreria de componentes UI

## Workflow por Tarea

### 1. Crear branch
```bash
git checkout main && git pull
git checkout -b feature/<issue-number>-<short-description>
```

### 2. Trabajar en la tarea
- Leer y entender el codigo existente antes de modificar
- Hacer commits frecuentes con mensajes descriptivos
- Seguir los patrones de collectors existentes

### 3. Documentar mientras se trabaja
- Agregar/actualizar docstrings
- Cada commit debe tener un mensaje claro que explique el "por que"

### 4. Al completar la tarea
- Crear un Pull Request con:
  - Titulo claro referenciando la tarea
  - Descripcion detallada de los cambios
  - Referencia al issue (`Closes #N`)
- Agregar issue al project si no esta:
  ```bash
  gh project item-add 4 --owner avelezX --url <issue-url>
  ```

### 5. Crear nuevas tareas si se descubren
```bash
gh issue create --repo avelezX/xerenity-dm --title "..." --body "..."
gh project item-add 4 --owner avelezX --url <issue-url>
```

## Convenciones de Commits
```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
Tipos: feat, fix, docs, refactor, test, chore
