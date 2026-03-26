-- Tabla para tracking de posiciones individuales de futuros (portafolio GR)
-- Ejecutar en Supabase SQL Editor

CREATE TABLE IF NOT EXISTS xerenity.risk_futures_portfolio (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    asset           TEXT NOT NULL,          -- MAIZ, AZUCAR, CACAO
    contract        TEXT NOT NULL,          -- Contrato especifico: ZCK26, SBN26, CCU26
    direction       TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    nominal         INTEGER NOT NULL,       -- Numero de contratos
    entry_price     NUMERIC NOT NULL,       -- Precio de compra/venta
    entry_date      DATE NOT NULL,          -- Fecha de entrada
    portfolio_id    TEXT,                    -- Opcional, para multi-portafolio
    active          BOOLEAN DEFAULT TRUE,   -- Posicion abierta o cerrada
    closed_date     DATE,                   -- Fecha de cierre (si aplica)
    closed_price    NUMERIC,                -- Precio de cierre (si aplica)
    rolled_to       TEXT,                   -- Contrato al que se rolo (si aplica)
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Constraint para upsert (merge-duplicates de Supabase REST)
ALTER TABLE xerenity.risk_futures_portfolio
    ADD CONSTRAINT uq_futures_position
    UNIQUE (asset, contract, entry_date, direction);

-- Indices para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_futures_portfolio_active
    ON xerenity.risk_futures_portfolio (active)
    WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_futures_portfolio_asset
    ON xerenity.risk_futures_portfolio (asset, active);

-- RLS: habilitar si se necesita control de acceso
-- ALTER TABLE xerenity.risk_futures_portfolio ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE xerenity.risk_futures_portfolio IS
    'Posiciones individuales de futuros para el portafolio de gestion de riesgos. Soporta LONG/SHORT, roll de contratos, y tracking de P&L.';
