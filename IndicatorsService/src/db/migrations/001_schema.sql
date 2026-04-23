-- IndicatorsService schema migration.
-- Creates symbol_indicators and symbol_patterns.
-- Strips technical indicator columns that moved out of symbol_metrics.
-- Idempotent — safe to re-run on startup.

CREATE TABLE IF NOT EXISTS symbol_indicators (
    symbol          VARCHAR(30) PRIMARY KEY REFERENCES symbols(symbol),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rsi_14          NUMERIC(6,2),
    macd_hist       NUMERIC(12,6),
    macd_hist_std   NUMERIC(12,6),
    roc_5           NUMERIC(9,4),
    roc_20          NUMERIC(9,4),
    roc_60          NUMERIC(9,4),
    vol_ratio_20    NUMERIC(8,4),
    adx_14          NUMERIC(6,2),
    plus_di         NUMERIC(6,2),
    minus_di        NUMERIC(6,2),
    weekly_bias     VARCHAR(10)  NOT NULL DEFAULT 'NEUTRAL',
    bb_squeeze      BOOLEAN      NOT NULL DEFAULT FALSE,
    squeeze_days    SMALLINT     NOT NULL DEFAULT 0,
    nr7             BOOLEAN      NOT NULL DEFAULT FALSE,
    atr_ratio       NUMERIC(8,4),
    atr_5           NUMERIC(14,4),
    bb_width        NUMERIC(10,6),
    kc_width        NUMERIC(10,6),
    rs_vs_nifty     NUMERIC(9,4),
    stage           VARCHAR(20)  NOT NULL DEFAULT 'UNKNOWN'
);

CREATE INDEX IF NOT EXISTS idx_symbol_indicators_stage
    ON symbol_indicators (stage)
    WHERE stage IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_symbol_indicators_computed_at
    ON symbol_indicators (computed_at DESC);

CREATE TABLE IF NOT EXISTS symbol_patterns (
    symbol             VARCHAR(30) PRIMARY KEY REFERENCES symbols(symbol),
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vcp_detected       BOOLEAN     NOT NULL DEFAULT FALSE,
    vcp_contractions   SMALLINT    NOT NULL DEFAULT 0,
    rect_breakout      BOOLEAN     NOT NULL DEFAULT FALSE,
    rect_range_pct     NUMERIC(6,2),
    consolidation_days SMALLINT    NOT NULL DEFAULT 0
);

-- Add ema_20 to symbol_metrics if not present (new structural metric).
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS ema_20 NUMERIC(14,4);

-- Drop indicator columns migrated to symbol_indicators.
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS atr_5;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS adx_14;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS plus_di;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS minus_di;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS bb_width;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS kc_width;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS bb_squeeze;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS squeeze_days;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS nr7;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS atr_ratio;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS rsi_14;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS macd_hist;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS roc_5;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS roc_20;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS roc_60;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS vol_ratio_20;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS rs_vs_nifty;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS weekly_bias;
ALTER TABLE symbol_metrics DROP COLUMN IF EXISTS stage;
