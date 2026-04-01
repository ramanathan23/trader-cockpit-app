-- MomentumScorerService schema.
-- Depends on DataSyncService having created the symbols table first.

CREATE TABLE IF NOT EXISTS momentum_scores (
    symbol       VARCHAR(30)   NOT NULL,
    timeframe    VARCHAR(10)   NOT NULL,  -- '1d' | '1m'
    score        NUMERIC(6,2)  NOT NULL,  -- 0–100 composite momentum score
    rsi          NUMERIC(6,2),
    macd_score   NUMERIC(6,2),
    roc_score    NUMERIC(6,2),
    vol_score    NUMERIC(6,2),
    computed_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_momentum_scores PRIMARY KEY (symbol, timeframe)
);

-- Fast descending score scan for top-N queries
CREATE INDEX IF NOT EXISTS idx_momentum_scores_daily
    ON momentum_scores(score DESC)
    WHERE timeframe = '1d';

CREATE INDEX IF NOT EXISTS idx_momentum_scores_1m
    ON momentum_scores(score DESC)
    WHERE timeframe = '1m';

CREATE INDEX IF NOT EXISTS idx_momentum_scores_computed
    ON momentum_scores(computed_at DESC);
