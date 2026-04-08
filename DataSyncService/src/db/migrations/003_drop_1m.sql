-- Migration 003: Drop 1-minute price data tables and related objects.
-- 1m sync was removed because Dhan's 10 000 req/day rate limit makes it
-- uneconomical to keep intraday data in sync across ~4 000 symbols.

-- Drop the continuous aggregate first (CASCADE removes its refresh policy).
DROP MATERIALIZED VIEW IF EXISTS price_1m_hourly CASCADE;

-- Drop the hypertable (CASCADE removes compression policy, chunks, indexes).
DROP TABLE IF EXISTS price_data_1m CASCADE;

-- Clean up any sync_state rows that tracked 1m data.
DELETE FROM sync_state WHERE timeframe = '1m';
