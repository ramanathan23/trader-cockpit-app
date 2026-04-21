-- ModelingService: database schema.
-- Idempotent — safe to re-run on startup.

-- ── model_predictions ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_predictions (
    id               BIGSERIAL    PRIMARY KEY,
    model_name       TEXT         NOT NULL,
    model_version    TEXT         NOT NULL,
    symbol           TEXT         NOT NULL,
    prediction_date  DATE         NOT NULL,
    predictions      JSONB        NOT NULL,
    confidence       REAL,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (model_name, symbol, prediction_date)
);

CREATE INDEX IF NOT EXISTS idx_predictions_model
    ON model_predictions(model_name, prediction_date DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol
    ON model_predictions(symbol, prediction_date DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_created
    ON model_predictions(created_at DESC);

-- ── service_config ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS service_config (
    service     VARCHAR(50)  NOT NULL,
    key         VARCHAR(100) NOT NULL,
    value       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (service, key)
);

CREATE INDEX IF NOT EXISTS idx_service_config_service
    ON service_config (service);
