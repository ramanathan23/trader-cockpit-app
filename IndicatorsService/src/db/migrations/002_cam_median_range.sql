-- Add cam_median_range_pct to symbol_metrics.
-- 60-day median of (high-low)*1.1/close per symbol.
-- LiveFeedService uses this as per-stock narrow-vs-wide Camarilla pivot threshold.
ALTER TABLE symbol_metrics
    ADD COLUMN IF NOT EXISTS cam_median_range_pct NUMERIC(10,6);
