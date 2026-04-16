-- DataSyncService baseline schema.
-- Consolidated from the existing incremental migrations and verified against the
-- current local database catalog on 2026-04-16.
--
-- All statements remain idempotent so the service can continue applying them on
-- startup without a migration history table.

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS symbols (
    symbol            VARCHAR(30) PRIMARY KEY,
    company_name      TEXT        NOT NULL,
    series            VARCHAR(10) NOT NULL DEFAULT 'EQ',
    isin              VARCHAR(20),
    listed_date       DATE,
    face_value        NUMERIC(10,2),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dhan_security_id  BIGINT,
    exchange_segment  VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_symbols_series
    ON symbols(series);

CREATE INDEX IF NOT EXISTS idx_symbols_dhan_id
    ON symbols(dhan_security_id)
    WHERE dhan_security_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS price_data_daily (
    time    TIMESTAMPTZ NOT NULL,
    symbol  VARCHAR(30) NOT NULL,
    open    NUMERIC(14,4),
    high    NUMERIC(14,4),
    low     NUMERIC(14,4),
    close   NUMERIC(14,4),
    volume  BIGINT,
    CONSTRAINT pk_price_daily PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'price_data_daily', 'time',
    partitioning_column    => 'symbol',
    number_partitions      => 8,
    chunk_time_interval    => INTERVAL '1 month',
    create_default_indexes => FALSE,
    if_not_exists          => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_daily_time_desc
    ON price_data_daily (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_daily_symbol_time_desc
    ON price_data_daily (symbol, time DESC);

ALTER TABLE price_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy(
    'price_data_daily',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE TABLE IF NOT EXISTS sync_state (
    symbol         VARCHAR(30) NOT NULL,
    timeframe      VARCHAR(10) NOT NULL,
    last_synced_at TIMESTAMPTZ,
    last_data_ts   TIMESTAMPTZ,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_msg      TEXT,
    CONSTRAINT pk_sync_state PRIMARY KEY (symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_status
    ON sync_state(status);

CREATE INDEX IF NOT EXISTS idx_sync_state_last_synced
    ON sync_state(last_synced_at ASC NULLS FIRST);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_symbol
    ON sync_state(timeframe, symbol);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_last_data
    ON sync_state(timeframe, last_data_ts ASC NULLS FIRST);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_last_synced
    ON sync_state(timeframe, last_synced_at ASC NULLS FIRST);

CREATE TABLE IF NOT EXISTS index_futures (
    id                SERIAL      PRIMARY KEY,
    underlying        VARCHAR(20) NOT NULL,
    dhan_security_id  BIGINT      NOT NULL,
    exchange_segment  VARCHAR(20) NOT NULL,
    lot_size          INTEGER     NOT NULL DEFAULT 1,
    expiry_date       DATE        NOT NULL,
    is_active         BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_index_futures_underlying_expiry UNIQUE (underlying, expiry_date)
);

CREATE INDEX IF NOT EXISTS idx_index_futures_active
    ON index_futures(underlying)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS symbol_metrics (
    symbol             VARCHAR(30) PRIMARY KEY,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    week52_high        NUMERIC(14,4),
    week52_low         NUMERIC(14,4),
    atr_14             NUMERIC(14,4),
    adv_20_cr          NUMERIC(10,2),
    trading_days       INTEGER,
    prev_day_high      NUMERIC(14,4),
    prev_day_low       NUMERIC(14,4),
    prev_day_close     NUMERIC(14,4),
    prev_week_high     NUMERIC(14,4),
    prev_week_low      NUMERIC(14,4),
    prev_month_high    NUMERIC(14,4),
    prev_month_low     NUMERIC(14,4),
    ema_50             NUMERIC(14,4),
    ema_200            NUMERIC(14,4),
    week_return_pct    NUMERIC(9,4),
    week_gain_pct      NUMERIC(9,4),
    week_decline_pct   NUMERIC(9,4)
);

CREATE INDEX IF NOT EXISTS idx_symbol_metrics_computed_at
    ON symbol_metrics (computed_at DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', time) AS bucket,
    symbol,
    FIRST(open, time)           AS open,
    MAX(high)                   AS high,
    MIN(low)                    AS low,
    LAST(close, time)           AS close,
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

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_monthly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', time) AS bucket,
    symbol,
    FIRST(open, time)            AS open,
    MAX(high)                    AS high,
    MIN(low)                     AS low,
    LAST(close, time)            AS close,
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

DELETE FROM sync_state WHERE timeframe = '1m';