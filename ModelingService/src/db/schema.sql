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
