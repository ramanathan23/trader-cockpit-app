-- Drop price_daily_weekly and price_daily_monthly continuous aggregate views.
-- Neither view is referenced by any service; removing to reduce schema noise.
DROP MATERIALIZED VIEW IF EXISTS price_daily_monthly CASCADE;
DROP MATERIALIZED VIEW IF EXISTS price_daily_weekly CASCADE;
