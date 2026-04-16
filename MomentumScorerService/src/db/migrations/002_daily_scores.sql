-- MomentumScorerService migration 002: Unified daily scores table.
-- Replaces the momentum_scores table with a richer unified scoring model
-- that captures momentum, trend, volatility compression, and structure.
-- All statements are idempotent.

-- ── Unified daily scores ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS daily_scores (
    symbol              VARCHAR(30)   NOT NULL,
    score_date          DATE          NOT NULL,
    total_score         NUMERIC(6,2)  NOT NULL,   -- 0–100 final composite
    momentum_score      NUMERIC(6,2),             -- RSI + MACD + ROC + volume
    trend_score         NUMERIC(6,2),             -- ADX + EMA alignment + weekly bias
    volatility_score    NUMERIC(6,2),             -- BB squeeze + ATR contraction + NR7
    structure_score     NUMERIC(6,2),             -- 52W proximity + relative strength + key levels
    rank                INTEGER,                  -- 1-based rank among all scored symbols
    is_watchlist        BOOLEAN       NOT NULL DEFAULT FALSE,  -- top 50 flag
    computed_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_daily_scores PRIMARY KEY (symbol, score_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_scores_date_rank
    ON daily_scores (score_date DESC, rank ASC);

CREATE INDEX IF NOT EXISTS idx_daily_scores_watchlist
    ON daily_scores (score_date DESC)
    WHERE is_watchlist = TRUE;

CREATE INDEX IF NOT EXISTS idx_daily_scores_total
    ON daily_scores (score_date DESC, total_score DESC);
