-- MomentumScorerService migration 003: Add ML comfort score column.

ALTER TABLE daily_scores 
ADD COLUMN IF NOT EXISTS comfort_score NUMERIC(6,2);

COMMENT ON COLUMN daily_scores.comfort_score IS 
'ML-predicted hold comfort score (0-100) from ModelingService. Higher = smoother ride, less psychological stress.';

CREATE INDEX IF NOT EXISTS idx_daily_scores_comfort
    ON daily_scores (score_date DESC, comfort_score DESC);
