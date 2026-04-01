-- DataSyncService schema
-- All statements are idempotent (IF NOT EXISTS) — safe to re-run on startup.

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── Symbols ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS symbols (
    symbol       VARCHAR(30)   PRIMARY KEY,
    company_name TEXT          NOT NULL,
    series       VARCHAR(10)   NOT NULL DEFAULT 'EQ',
    isin         VARCHAR(20),
    listed_date  DATE,
    face_value   NUMERIC(10,2),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_symbols_series ON symbols(series);

-- ── 1-Minute OHLCV ───────────────────────────────────────────────────────────
-- chunk_time_interval = 1 day: ~2131 symbols × 375 bars/day = ~800k rows/chunk
-- TimescaleDB recommended chunk size: 25-250MB → 1 day is appropriate here.

CREATE TABLE IF NOT EXISTS price_data_1m (
    time    TIMESTAMPTZ   NOT NULL,
    symbol  VARCHAR(30)   NOT NULL,
    open    NUMERIC(14,4),
    high    NUMERIC(14,4),
    low     NUMERIC(14,4),
    close   NUMERIC(14,4),
    volume  BIGINT,
    CONSTRAINT pk_price_1m PRIMARY KEY (time, symbol)
);

SELECT create_hypertable(
    'price_data_1m', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_1m_sym_time
    ON price_data_1m (symbol, time DESC);

ALTER TABLE price_data_1m SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('price_data_1m', INTERVAL '7 days', if_not_exists => TRUE);

-- ── Daily OHLCV ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS price_data_daily (
    time    TIMESTAMPTZ   NOT NULL,
    symbol  VARCHAR(30)   NOT NULL,
    open    NUMERIC(14,4),
    high    NUMERIC(14,4),
    low     NUMERIC(14,4),
    close   NUMERIC(14,4),
    volume  BIGINT,
    CONSTRAINT pk_price_daily PRIMARY KEY (time, symbol)
);

SELECT create_hypertable(
    'price_data_daily', 'time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_daily_sym_time
    ON price_data_daily (symbol, time DESC);

ALTER TABLE price_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('price_data_daily', INTERVAL '30 days', if_not_exists => TRUE);

-- ── Sync state ────────────────────────────────────────────────────────────────
-- Tracks last successful sync per (symbol, timeframe) pair.

CREATE TABLE IF NOT EXISTS sync_state (
    symbol         VARCHAR(30)  NOT NULL,
    timeframe      VARCHAR(10)  NOT NULL,   -- '1m' | '1d'
    last_synced_at TIMESTAMPTZ,
    last_data_ts   TIMESTAMPTZ,             -- most recent bar timestamp in DB
    status         VARCHAR(20)  NOT NULL DEFAULT 'pending',
    error_msg      TEXT,
    CONSTRAINT pk_sync_state PRIMARY KEY (symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_status      ON sync_state(status);
CREATE INDEX IF NOT EXISTS idx_sync_state_last_synced ON sync_state(last_synced_at ASC NULLS FIRST);

-- ── Hourly continuous aggregate (from 1m data) ────────────────────────────────
-- Used by MomentumScorerService for intraday momentum signals.

CREATE MATERIALIZED VIEW IF NOT EXISTS price_1m_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    FIRST(open,  time)          AS open,
    MAX(high)                   AS high,
    MIN(low)                    AS low,
    LAST(close,  time)          AS close,
    SUM(volume)                 AS volume
FROM price_data_1m
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_1m_hourly',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ── Weekly continuous aggregate (from daily data) ─────────────────────────────
-- Time-compressed view of price_data_daily bucketed by ISO week.

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', time) AS bucket,
    symbol,
    FIRST(open,  time)          AS open,
    MAX(high)                   AS high,
    MIN(low)                    AS low,
    LAST(close,  time)          AS close,
    SUM(volume)                 AS volume
FROM price_data_daily
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_daily_weekly',
    start_offset      => INTERVAL '1 month',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists     => TRUE
);

-- ── Monthly continuous aggregate (from daily data) ────────────────────────────
-- Time-compressed view of price_data_daily bucketed by calendar month.

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_monthly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', time) AS bucket,
    symbol,
    FIRST(open,  time)           AS open,
    MAX(high)                    AS high,
    MIN(low)                     AS low,
    LAST(close,  time)           AS close,
    SUM(volume)                  AS volume
FROM price_data_daily
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_daily_monthly',
    start_offset      => INTERVAL '3 months',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists     => TRUE
);
