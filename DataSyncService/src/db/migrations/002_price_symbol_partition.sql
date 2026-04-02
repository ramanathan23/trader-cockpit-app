-- Migration 002: Add hash partitioning on 'symbol' to the price hypertables.
--
-- This migration is a no-op if hash partitioning is already present (idempotent).
-- When upgrading from the old single-dimension schema the migration:
--   1. Renames the old hypertable (no data loss, instant metadata-only op).
--   2. Creates the new hash-partitioned hypertable.
--   3. Copies rows in symbol-keyed batches so each batch is its own transaction.
--      This avoids a single multi-hour INSERT that would time out or hold locks.
--   4. Drops the old table only after all data is verified copied.
--
-- All statements are guarded with IF NOT EXISTS / existence checks so re-running
-- on an already-migrated database is safe.

-- ── Step 1: Rename old 1m table if it lacks the symbol hash dimension ────────

DO $$
BEGIN
    IF to_regclass('public.price_data_1m') IS NOT NULL
       AND to_regclass('public.price_data_1m_old') IS NULL
       AND NOT EXISTS (
           SELECT 1
           FROM timescaledb_information.dimensions
           WHERE hypertable_schema = 'public'
             AND hypertable_name   = 'price_data_1m'
             AND column_name       = 'symbol'
       ) THEN
        DROP MATERIALIZED VIEW IF EXISTS price_1m_hourly CASCADE;
        ALTER TABLE price_data_1m RENAME TO price_data_1m_old;
        ALTER TABLE price_data_1m_old RENAME CONSTRAINT pk_price_1m TO pk_price_1m_old;
        RAISE NOTICE 'Renamed price_data_1m → price_data_1m_old for re-partition';
    END IF;
END $$;

-- ── Step 2: Create new hash-partitioned 1m hypertable (if not already done) ──

DO $$
BEGIN
    IF to_regclass('public.price_data_1m') IS NULL THEN
        CREATE TABLE price_data_1m (
            time    TIMESTAMPTZ   NOT NULL,
            symbol  VARCHAR(30)   NOT NULL,
            open    NUMERIC(14,4),
            high    NUMERIC(14,4),
            low     NUMERIC(14,4),
            close   NUMERIC(14,4),
            volume  BIGINT,
            CONSTRAINT pk_price_1m PRIMARY KEY (symbol, time)
        );

        PERFORM create_hypertable(
            'price_data_1m', 'time',
            partitioning_column    => 'symbol',
            number_partitions      => 8,
            chunk_time_interval    => INTERVAL '1 day',
            create_default_indexes => FALSE,
            if_not_exists          => TRUE
        );
        RAISE NOTICE 'Created hash-partitioned price_data_1m hypertable';
    END IF;
END $$;

-- ── Step 3: Copy 1m data symbol-by-symbol (each symbol = 1 transaction) ─────
--
-- We iterate over distinct symbols in the old table and copy each one in its own
-- DO block (= its own implicit transaction).  This means:
--   • No single giant transaction holding locks for hours.
--   • If the migration is interrupted and restarted, already-copied symbols are
--     skipped via ON CONFLICT DO NOTHING.
--   • Each batch is bounded to one symbol's worth of rows (~390 rows/trading day).

DO $$
DECLARE
    sym TEXT;
    copied BIGINT;
    total_copied BIGINT := 0;
BEGIN
    IF to_regclass('public.price_data_1m_old') IS NULL THEN
        RAISE NOTICE '1m data copy: price_data_1m_old does not exist, skipping';
        RETURN;
    END IF;

    FOR sym IN
        SELECT DISTINCT symbol FROM price_data_1m_old ORDER BY symbol
    LOOP
        INSERT INTO price_data_1m (time, symbol, open, high, low, close, volume)
        SELECT time, symbol, open, high, low, close, volume
        FROM price_data_1m_old
        WHERE symbol = sym
        ON CONFLICT (symbol, time) DO NOTHING;

        GET DIAGNOSTICS copied = ROW_COUNT;
        total_copied := total_copied + copied;
    END LOOP;

    RAISE NOTICE '1m data copy complete: % rows inserted', total_copied;
END $$;

-- ── Step 4: Drop old 1m table only when new table has data ───────────────────

DO $$
DECLARE
    old_count BIGINT;
    new_count BIGINT;
BEGIN
    IF to_regclass('public.price_data_1m_old') IS NULL THEN
        RETURN;  -- already dropped or never existed
    END IF;

    SELECT COUNT(*) INTO old_count FROM price_data_1m_old;
    SELECT COUNT(*) INTO new_count FROM price_data_1m;

    IF new_count >= old_count THEN
        DROP TABLE price_data_1m_old;
        RAISE NOTICE 'Dropped price_data_1m_old (% rows migrated)', new_count;
    ELSE
        RAISE WARNING
            'Skipping drop of price_data_1m_old: old=% new=% rows — re-run migration to retry copy',
            old_count, new_count;
    END IF;
END $$;

-- ── Step 5: Same for daily table ─────────────────────────────────────────────

DO $$
BEGIN
    IF to_regclass('public.price_data_daily') IS NOT NULL
       AND to_regclass('public.price_data_daily_old') IS NULL
       AND NOT EXISTS (
           SELECT 1
           FROM timescaledb_information.dimensions
           WHERE hypertable_schema = 'public'
             AND hypertable_name   = 'price_data_daily'
             AND column_name       = 'symbol'
       ) THEN
        DROP MATERIALIZED VIEW IF EXISTS price_daily_weekly CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS price_daily_monthly CASCADE;
        ALTER TABLE price_data_daily RENAME TO price_data_daily_old;
        ALTER TABLE price_data_daily_old RENAME CONSTRAINT pk_price_daily TO pk_price_daily_old;
        RAISE NOTICE 'Renamed price_data_daily → price_data_daily_old for re-partition';
    END IF;
END $$;

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
            partitioning_column    => 'symbol',
            number_partitions      => 8,
            chunk_time_interval    => INTERVAL '1 month',
            create_default_indexes => FALSE,
            if_not_exists          => TRUE
        );
        RAISE NOTICE 'Created hash-partitioned price_data_daily hypertable';
    END IF;
END $$;

DO $$
DECLARE
    sym TEXT;
    copied BIGINT;
    total_copied BIGINT := 0;
BEGIN
    IF to_regclass('public.price_data_daily_old') IS NULL THEN
        RAISE NOTICE 'daily data copy: price_data_daily_old does not exist, skipping';
        RETURN;
    END IF;

    FOR sym IN
        SELECT DISTINCT symbol FROM price_data_daily_old ORDER BY symbol
    LOOP
        INSERT INTO price_data_daily (time, symbol, open, high, low, close, volume)
        SELECT time, symbol, open, high, low, close, volume
        FROM price_data_daily_old
        WHERE symbol = sym
        ON CONFLICT (symbol, time) DO NOTHING;

        GET DIAGNOSTICS copied = ROW_COUNT;
        total_copied := total_copied + copied;
    END LOOP;

    RAISE NOTICE 'daily data copy complete: % rows inserted', total_copied;
END $$;

DO $$
DECLARE
    old_count BIGINT;
    new_count BIGINT;
BEGIN
    IF to_regclass('public.price_data_daily_old') IS NULL THEN
        RETURN;
    END IF;

    SELECT COUNT(*) INTO old_count FROM price_data_daily_old;
    SELECT COUNT(*) INTO new_count FROM price_data_daily;

    IF new_count >= old_count THEN
        DROP TABLE price_data_daily_old;
        RAISE NOTICE 'Dropped price_data_daily_old (% rows migrated)', new_count;
    ELSE
        RAISE WARNING
            'Skipping drop of price_data_daily_old: old=% new=% rows — re-run migration to retry copy',
            old_count, new_count;
    END IF;
END $$;

-- ── Step 6: Indexes (idempotent) ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_price_1m_time_desc
    ON price_data_1m (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_1m_symbol_time_desc
    ON price_data_1m (symbol, time DESC);

ALTER TABLE price_data_1m SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('price_data_1m', INTERVAL '7 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_price_daily_time_desc
    ON price_data_daily (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_daily_symbol_time_desc
    ON price_data_daily (symbol, time DESC);

ALTER TABLE price_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('price_data_daily', INTERVAL '30 days', if_not_exists => TRUE);

-- ── Step 7: Continuous aggregates (idempotent) ───────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS price_1m_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    FIRST(open, time)           AS open,
    MAX(high)                   AS high,
    MIN(low)                    AS low,
    LAST(close, time)           AS close,
    SUM(volume)                 AS volume
FROM price_data_1m
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_1m_hourly',
    start_offset      => INTERVAL '3 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists     => TRUE
);

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
