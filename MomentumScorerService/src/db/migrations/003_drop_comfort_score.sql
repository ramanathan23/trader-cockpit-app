-- Remove comfort_score from daily_scores.
-- Comfort scores are now stored in model_predictions (ModelingService).
ALTER TABLE daily_scores DROP COLUMN IF EXISTS comfort_score;
DROP INDEX IF EXISTS idx_daily_scores_comfort;
