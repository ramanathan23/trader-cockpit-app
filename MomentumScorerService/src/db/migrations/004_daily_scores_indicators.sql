-- MomentumScorerService migration 004: Embed computed indicator values in daily_scores.
--
-- Rationale: daily_scores is the only time-series source for historical indicator values.
-- symbol_metrics is a latest-snapshot table (written by DataSyncService for structural
-- context and updated by MomentumScorerService for live display). Storing indicator values
-- in daily_scores eliminates look-ahead bias in ML training datasets and removes the need
-- to JOIN symbol_metrics for historical feature retrieval.
-- All statements are idempotent.

ALTER TABLE daily_scores
    ADD COLUMN IF NOT EXISTS rsi_14       NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS macd_hist    NUMERIC(12,6),
    ADD COLUMN IF NOT EXISTS roc_5        NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS roc_20       NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS roc_60       NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS vol_ratio_20 NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS adx_14       NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS plus_di      NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS minus_di     NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS weekly_bias  VARCHAR(10),
    ADD COLUMN IF NOT EXISTS bb_squeeze   BOOLEAN,
    ADD COLUMN IF NOT EXISTS squeeze_days INTEGER,
    ADD COLUMN IF NOT EXISTS nr7          BOOLEAN,
    ADD COLUMN IF NOT EXISTS atr_ratio    NUMERIC(8,4),
    ADD COLUMN IF NOT EXISTS atr_5        NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS bb_width     NUMERIC(12,6),
    ADD COLUMN IF NOT EXISTS kc_width     NUMERIC(12,6),
    ADD COLUMN IF NOT EXISTS rs_vs_nifty  NUMERIC(8,4);
