-- Migration 004: 1-minute OHLCV table for F&O stocks (Dhan historical API).
-- Idempotent. Weekly chunks; compress after 7 days.

CREATE TABLE IF NOT EXISTS price_data_1min (
    time    TIMESTAMPTZ NOT NULL,
    symbol  VARCHAR(30) NOT NULL,
    open    NUMERIC(10,4),
    high    NUMERIC(10,4),
    low     NUMERIC(10,4),
    close   NUMERIC(10,4),
    volume  BIGINT,
    CONSTRAINT pk_price_1min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'price_data_1min', 'time',
    partitioning_column    => 'symbol',
    number_partitions      => 4,
    chunk_time_interval    => INTERVAL '1 week',
    create_default_indexes => FALSE,
    if_not_exists          => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_1min_time_desc
    ON price_data_1min (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_1min_symbol_time_desc
    ON price_data_1min (symbol, time DESC);

ALTER TABLE price_data_1min SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy(
    'price_data_1min',
    INTERVAL '7 days',
    if_not_exists => TRUE
);
