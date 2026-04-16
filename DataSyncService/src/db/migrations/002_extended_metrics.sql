-- DataSyncService migration 002: Extended symbol_metrics for unified scoring.
-- Adds volatility-compression, trend-quality, and structure columns
-- used by the unified scorer to rank symbols pre-market.
-- All statements are idempotent.

-- ── New columns on symbol_metrics ────────────────────────────────────────────

ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS atr_5         NUMERIC(14,4);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS adx_14        NUMERIC(6,2);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS plus_di       NUMERIC(6,2);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS minus_di      NUMERIC(6,2);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS bb_width      NUMERIC(10,6);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS kc_width      NUMERIC(10,6);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS bb_squeeze    BOOLEAN DEFAULT FALSE;
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS squeeze_days  INTEGER DEFAULT 0;
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS nr7           BOOLEAN DEFAULT FALSE;
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS atr_ratio     NUMERIC(6,4);  -- ATR(5)/ATR(14)
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS rsi_14        NUMERIC(6,2);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS macd_hist     NUMERIC(12,4);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS roc_5         NUMERIC(9,4);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS roc_20        NUMERIC(9,4);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS roc_60        NUMERIC(9,4);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS vol_ratio_20  NUMERIC(6,2);
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS rs_vs_nifty   NUMERIC(9,4);  -- relative strength vs NIFTY500
ALTER TABLE symbol_metrics ADD COLUMN IF NOT EXISTS weekly_bias   VARCHAR(10) DEFAULT 'NEUTRAL';  -- BULLISH/BEARISH/NEUTRAL
