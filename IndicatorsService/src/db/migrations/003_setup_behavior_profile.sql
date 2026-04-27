DROP TABLE IF EXISTS symbol_intraday_profile;

CREATE TABLE IF NOT EXISTS symbol_setup_behavior_profile (
    symbol                    VARCHAR(30) PRIMARY KEY REFERENCES symbols(symbol),
    computed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sessions_analyzed         INTEGER     NOT NULL DEFAULT 0,
    setups_analyzed           INTEGER     NOT NULL DEFAULT 0,
    breakout_attempts         INTEGER     NOT NULL DEFAULT 0,
    breakdown_attempts        INTEGER     NOT NULL DEFAULT 0,
    reversal_attempts         INTEGER     NOT NULL DEFAULT 0,
    breakout_success_rate     NUMERIC(6,4),
    breakdown_success_rate    NUMERIC(6,4),
    reversal_success_rate     NUMERIC(6,4),
    fakeout_rate              NUMERIC(6,4),
    deep_pullback_rate        NUMERIC(6,4),
    avg_adverse_excursion_r   NUMERIC(8,4),
    avg_pullback_depth_r      NUMERIC(8,4),
    avg_time_to_1r_bars       NUMERIC(8,4),
    trend_efficiency          NUMERIC(6,4),
    vwap_hold_rate            NUMERIC(6,4),
    avg_session_turnover_cr   NUMERIC(12,2),
    liquidity_score           NUMERIC(6,2),
    breakout_quality_score    NUMERIC(6,2),
    breakdown_quality_score   NUMERIC(6,2),
    reversal_quality_score    NUMERIC(6,2),
    execution_score           NUMERIC(6,2),
    execution_grade           VARCHAR(20) NOT NULL DEFAULT 'NA'
);

CREATE INDEX IF NOT EXISTS idx_setup_behavior_computed
    ON symbol_setup_behavior_profile (computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_setup_behavior_execution
    ON symbol_setup_behavior_profile (execution_score DESC);

CREATE INDEX IF NOT EXISTS idx_setup_behavior_grade
    ON symbol_setup_behavior_profile (execution_grade);
