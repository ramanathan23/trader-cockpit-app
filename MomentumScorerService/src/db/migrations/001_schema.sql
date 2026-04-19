-- MomentumScorerService: consolidated schema.
-- daily_scores is the unified scoring table. Includes embedded indicator columns
-- for historical ML feature retrieval (eliminates look-ahead bias, no JOIN needed).
-- Idempotent — safe to re-run on startup.

CREATE TABLE IF NOT EXISTS daily_scores (
    symbol              VARCHAR(30)   NOT NULL,
    score_date          DATE          NOT NULL,
    total_score         NUMERIC(6,2)  NOT NULL,
    momentum_score      NUMERIC(6,2),
    trend_score         NUMERIC(6,2),
    volatility_score    NUMERIC(6,2),
    structure_score     NUMERIC(6,2),
    rank                INTEGER,
    is_watchlist        BOOLEAN       NOT NULL DEFAULT FALSE,
    computed_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- Embedded indicator snapshot
    rsi_14              NUMERIC(8,4),
    macd_hist           NUMERIC(12,6),
    roc_5               NUMERIC(8,4),
    roc_20              NUMERIC(8,4),
    roc_60              NUMERIC(8,4),
    vol_ratio_20        NUMERIC(8,4),
    adx_14              NUMERIC(8,4),
    plus_di             NUMERIC(8,4),
    minus_di            NUMERIC(8,4),
    weekly_bias         VARCHAR(10),
    bb_squeeze          BOOLEAN,
    squeeze_days        INTEGER,
    nr7                 BOOLEAN,
    atr_ratio           NUMERIC(8,4),
    atr_5               NUMERIC(12,4),
    bb_width            NUMERIC(12,6),
    kc_width            NUMERIC(12,6),
    rs_vs_nifty         NUMERIC(8,4),
    CONSTRAINT pk_daily_scores PRIMARY KEY (symbol, score_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_scores_date_rank
    ON daily_scores (score_date DESC, rank ASC);

CREATE INDEX IF NOT EXISTS idx_daily_scores_watchlist
    ON daily_scores (score_date DESC)
    WHERE is_watchlist = TRUE;

CREATE INDEX IF NOT EXISTS idx_daily_scores_total
    ON daily_scores (score_date DESC, total_score DESC);


