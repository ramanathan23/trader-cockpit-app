-- Migration 002: Configure price hypertables with compression and continuous aggregates.
--
-- All statements are idempotent (IF NOT EXISTS / existence checks).

-- ── daily hypertable ──────────────────────────────────────────────────────────

DO $$
BEGIN
    IF to_regclass('public.price_data_daily') IS NULL THEN
        CREATE TABLE price_data_daily (
            time    TIMESTAMPTZ   NOT NULL,
            symbol  VARCHAR(30)   NOT NULL,
            open    NUMERIC(14,4),
            high    NUMERIC(14,4),
            low     NUMERIC(14,4),
            close   NUMERIC(14,4),
            volume  BIGINT,
            CONSTRAINT pk_price_daily PRIMARY KEY (symbol, time)
        );

        PERFORM create_hypertable(
            'price_data_daily', 'time',
            chunk_time_interval    => INTERVAL '1 month',
            create_default_indexes => FALSE,
            if_not_exists          => TRUE
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_price_daily_symbol_time_desc
    ON price_data_daily (symbol, time DESC);

ALTER TABLE price_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('price_data_daily', INTERVAL '30 days', if_not_exists => TRUE);

-- ── continuous aggregates ─────────────────────────────────────────────────────

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
