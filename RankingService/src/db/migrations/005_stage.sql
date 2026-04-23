-- Add stage column to daily_scores and symbol_metrics.
-- Idempotent — safe to re-run on startup.

ALTER TABLE daily_scores    ADD COLUMN IF NOT EXISTS stage VARCHAR(10);
ALTER TABLE symbol_metrics  ADD COLUMN IF NOT EXISTS stage VARCHAR(10);

CREATE INDEX IF NOT EXISTS idx_daily_scores_stage
    ON daily_scores (score_date DESC, stage)
    WHERE stage IS NOT NULL;
