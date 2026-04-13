-- Precomputed per-symbol daily metrics, refreshed after each 1d EOD sync.
-- LiveFeedService reads from this table instead of computing at startup.

CREATE TABLE IF NOT EXISTS symbol_metrics (
    symbol           VARCHAR(30) PRIMARY KEY,
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Rolling window metrics
    week52_high      NUMERIC(14,4),
    week52_low       NUMERIC(14,4),
    atr_14           NUMERIC(14,4),
    adv_20_cr        NUMERIC(10,2),
    trading_days     INTEGER,

    -- Previous trading day
    prev_day_high    NUMERIC(14,4),
    prev_day_low     NUMERIC(14,4),
    prev_day_close   NUMERIC(14,4),

    -- Previous calendar week (Mon–Sun)
    prev_week_high   NUMERIC(14,4),
    prev_week_low    NUMERIC(14,4),

    -- Previous calendar month
    prev_month_high  NUMERIC(14,4),
    prev_month_low   NUMERIC(14,4)
);

CREATE INDEX IF NOT EXISTS idx_symbol_metrics_computed_at
    ON symbol_metrics (computed_at DESC);
