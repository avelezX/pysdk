# xerenity-backend - Claude Agent Workflow

## Project Info
- **GitHub Org:** avelezX
- **Repo:** xerenity-backend (formerly pysdk)
- **GitHub Project:** Xerenity (#4)
- **Description:** Backend consolidado — pricing, risk management, data collectors, core SDK

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
   - Repo asociado (filtrar las relevantes a este repo: pysdk)
   - Prioridad si la tiene
   Filtrar y mostrar primero las tareas "In Progress" y "Todo".

3. **Preguntar cual tarea trabajar** - Si el usuario no especifica, preguntar cual tarea del backlog quiere abordar.

## Repos del ecosistema Xerenity (consolidado marzo 2026)
- **xerenity-backend** - Backend consolidado: pricing, risk, data collectors, core SDK (este repo)
- **xerenity-fe** - Frontend (Next.js/TypeScript, deploy Vercel)
- **xerenity-py** - Librería pública PyPI para clientes (v0.3.0)
- **xerenity-db** - Migraciones y esquema DB (SQL/Supabase)
- **xerenity** - Landing page / redirect

### Archivados
- xerenity-api, ui-components (archivados, código absorbido o sin uso)
- xerenity-dm (código en dm/ de este repo, pendiente archivar)

## Estructura del monorepo
```
xerenity-backend/
├── pricing/           # Instrumentos financieros (NDF, CCS, TES, swaps)
├── gestion_de_riesgos/ # VaR, exposición, portafolio de riesgo
├── server/            # Django API (pricing_api, risk_management_server)
├── src/               # Módulos core (xerenity, collectors)
├── dm/                # Data management (collectors de xerenity-dm)
├── core-sdk/          # Core SDK original (connection, search, marks, loans)
├── notebooks/         # Jupyter notebooks de ejemplo
├── fly.toml           # Deploy Fly.io (app: xerenity-pysdk)
└── Dockerfile
```

## Workflow por Tarea

### 1. Crear branch
```bash
git checkout main && git pull
git checkout -b feature/<issue-number>-<short-description>
```

### 2. Trabajar en la tarea
- Leer y entender el codigo existente antes de modificar
- Hacer commits frecuentes con mensajes descriptivos
- Seguir las convenciones del proyecto existente

### 3. Documentar mientras se trabaja
- Si hay cambios significativos, actualizar documentacion relevante
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
gh issue create --repo avelezX/xerenity-backend --title "..." --body "..."
gh project item-add 4 --owner avelezX --url <issue-url>
```

## Convenciones de Commits
```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
Tipos: feat, fix, docs, refactor, test, chore
