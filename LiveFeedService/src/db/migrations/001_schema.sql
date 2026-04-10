-- LiveFeedService schema.
-- Depends on DataSyncService migration 004 having run first
-- (symbols.dhan_security_id and index_futures table must exist).
-- All statements are idempotent.

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 3-minute OHLCV candles for all subscribed equities.
CREATE TABLE IF NOT EXISTS candles_3min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(30)    NOT NULL,
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_candles_3min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'candles_3min', 'time',
    partitioning_column => 'symbol',
    number_partitions   => 16,
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_candles_3min_symbol_time
    ON candles_3min (symbol, time DESC);

-- 3-minute candles for index futures (NIFTY / BANKNIFTY / SENSEX market proxy).
CREATE TABLE IF NOT EXISTS index_future_candles_3min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(20)    NOT NULL,   -- underlying: NIFTY | BANKNIFTY | SENSEX
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_idx_fut_candles PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'index_future_candles_3min', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_fut_candles_symbol_time
    ON index_future_candles_3min (symbol, time DESC);
