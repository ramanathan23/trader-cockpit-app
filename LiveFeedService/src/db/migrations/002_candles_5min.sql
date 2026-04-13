-- LiveFeedService migration 002: 5-minute candle tables.
-- Switches primary candle resolution from 3-min to 5-min.
-- Old candles_3min tables are retained (no data loss).
-- All statements are idempotent.

-- 5-minute OHLCV candles for all subscribed equities.
CREATE TABLE IF NOT EXISTS candles_5min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(30)    NOT NULL,
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_candles_5min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'candles_5min', 'time',
    partitioning_column => 'symbol',
    number_partitions   => 16,
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_candles_5min_symbol_time
    ON candles_5min (symbol, time DESC);

-- 5-minute candles for index futures.
CREATE TABLE IF NOT EXISTS index_future_candles_5min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(20)    NOT NULL,
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_idx_fut_candles_5min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'index_future_candles_5min', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_fut_candles_5min_symbol_time
    ON index_future_candles_5min (symbol, time DESC);
