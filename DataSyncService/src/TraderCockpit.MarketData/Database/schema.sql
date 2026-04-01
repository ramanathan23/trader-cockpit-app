-- ============================================================
-- TimescaleDB Schema for TraderCockpit Market Data
-- ============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- -----------------------------------------------------------
-- 1. Symbols
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS symbols (
    id               SERIAL       PRIMARY KEY,
    symbol           VARCHAR(50)  NOT NULL UNIQUE,
    company_name     VARCHAR(500) NOT NULL,
    series           VARCHAR(10)  NOT NULL,
    isin             VARCHAR(20)  NOT NULL,
    -- Populated separately from Dhan's securities master CSV.
    -- Sync is skipped for symbols where this is NULL.
    dhan_security_id VARCHAR(20),
    exchange_segment VARCHAR(20)  NOT NULL DEFAULT 'NSE_EQ',
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_symbols_dhan_id
    ON symbols (dhan_security_id)
    WHERE dhan_security_id IS NOT NULL;

-- -----------------------------------------------------------
-- 2. 1-Minute Hypertable
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_data_1m (
    time        TIMESTAMPTZ   NOT NULL,
    symbol_id   INTEGER       NOT NULL REFERENCES symbols(id),
    open        NUMERIC(14,4) NOT NULL,
    high        NUMERIC(14,4) NOT NULL,
    low         NUMERIC(14,4) NOT NULL,
    close       NUMERIC(14,4) NOT NULL,
    volume      BIGINT        NOT NULL
);

SELECT create_hypertable(
    'price_data_1m',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

-- Ensures upsert safety (ON CONFLICT target)
CREATE UNIQUE INDEX IF NOT EXISTS uix_price_data_1m_time_symbol
    ON price_data_1m (time, symbol_id);

-- -----------------------------------------------------------
-- 3. Compression (chunks older than 7 days)
-- -----------------------------------------------------------
ALTER TABLE price_data_1m SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol_id',
    timescaledb.compress_orderby   = 'time DESC'
);

SELECT add_compression_policy(
    'price_data_1m',
    compress_after => INTERVAL '7 days',
    if_not_exists  => TRUE
);

-- -----------------------------------------------------------
-- 4. Continuous Aggregates
-- Query these views directly — no C# aggregation needed.
-- Window functions for Momentum Scores work across all views:
--   close / LAG(close, N) OVER (PARTITION BY symbol_id ORDER BY bucket)
-- -----------------------------------------------------------

-- 5-minute
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    symbol_id,
    FIRST(open,  time) AS open,
    MAX(high)          AS high,
    MIN(low)           AS low,
    LAST(close,  time) AS close,
    SUM(volume)        AS volume
FROM price_data_1m
GROUP BY bucket, symbol_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('price_data_5m',
    start_offset      => INTERVAL '2 hours',
    end_offset        => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists     => TRUE);

-- 15-minute
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', time) AS bucket,
    symbol_id,
    FIRST(open,  time) AS open,
    MAX(high)          AS high,
    MIN(low)           AS low,
    LAST(close,  time) AS close,
    SUM(volume)        AS volume
FROM price_data_1m
GROUP BY bucket, symbol_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('price_data_15m',
    start_offset      => INTERVAL '6 hours',
    end_offset        => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists     => TRUE);

-- Daily
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol_id,
    FIRST(open,  time) AS open,
    MAX(high)          AS high,
    MIN(low)           AS low,
    LAST(close,  time) AS close,
    SUM(volume)        AS volume
FROM price_data_1m
GROUP BY bucket, symbol_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('price_data_daily',
    start_offset      => INTERVAL '3 days',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists     => TRUE);

-- -----------------------------------------------------------
-- 5. Sync Runs — one row per full-universe sync trigger
-- -----------------------------------------------------------
-- Each POST /sync creates exactly one row here tracking the
-- entire backfill/update run across all symbols.
-- Status: InProgress | Completed | Failed
CREATE TABLE IF NOT EXISTS sync_runs (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    status           VARCHAR(20) NOT NULL DEFAULT 'InProgress',
    total_symbols    INTEGER     NOT NULL DEFAULT 0,
    symbols_updated  INTEGER     NOT NULL DEFAULT 0,
    symbols_skipped  INTEGER     NOT NULL DEFAULT 0,
    symbols_failed   INTEGER     NOT NULL DEFAULT 0,
    current_symbol   VARCHAR(50),
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at      TIMESTAMPTZ,
    error_message    TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_runs_status ON sync_runs (status);

-- -----------------------------------------------------------
-- 6. Daily Raw Hypertable
-- Stores EOD bars fetched directly from Dhan's historical API
-- (up to BackfillDailyYears, default 5 years).
-- Independent of price_data_1m — not derived by aggregation.
-- The price_data_daily continuous aggregate (section 4) still
-- exists for deriving daily candles from 1m data, but queries
-- for the "daily" timeframe read from this table instead.
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_data_daily_raw (
    time        TIMESTAMPTZ   NOT NULL,
    symbol_id   INTEGER       NOT NULL REFERENCES symbols(id),
    open        NUMERIC(14,4) NOT NULL,
    high        NUMERIC(14,4) NOT NULL,
    low         NUMERIC(14,4) NOT NULL,
    close       NUMERIC(14,4) NOT NULL,
    volume      BIGINT        NOT NULL
);

SELECT create_hypertable(
    'price_data_daily_raw',
    'time',
    chunk_time_interval => INTERVAL '1 year',
    if_not_exists       => TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS uix_price_data_daily_raw_time_symbol
    ON price_data_daily_raw (time, symbol_id);

ALTER TABLE price_data_daily_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol_id',
    timescaledb.compress_orderby   = 'time DESC'
);

SELECT add_compression_policy(
    'price_data_daily_raw',
    compress_after => INTERVAL '30 days',
    if_not_exists  => TRUE
);
