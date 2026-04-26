CREATE TABLE IF NOT EXISTS intraday_training_sessions (
    symbol                  VARCHAR(30)   NOT NULL,
    session_date            DATE          NOT NULL,
    prev_rsi                NUMERIC(8,4),
    prev_adx                NUMERIC(8,4),
    prev_di_spread          NUMERIC(8,4),
    prev_atr_ratio          NUMERIC(8,4),
    prev_roc_5              NUMERIC(8,4),
    prev_roc_20             NUMERIC(8,4),
    prev_vol_ratio          NUMERIC(8,4),
    prev_bb_squeeze         BOOLEAN,
    prev_squeeze_days       INTEGER,
    prev_rs_vs_nifty        NUMERIC(8,4),
    stage_encoded           SMALLINT,
    day_of_week             SMALLINT,
    nifty_gap_pct           NUMERIC(8,4),
    iss_score               NUMERIC(6,2),
    choppiness_idx          NUMERIC(8,4),
    stop_hunt_rate          NUMERIC(6,4),
    orb_followthrough_rate  NUMERIC(6,4),
    pullback_depth_hist     NUMERIC(6,4),
    high_close_ratio        NUMERIC(6,4),
    range_vs_atr            NUMERIC(6,4),
    pullback_depth          NUMERIC(6,4),
    session_type            VARCHAR(15),
    trend_up                BOOLEAN,
    trend_down              BOOLEAN,
    chop_day                BOOLEAN,
    volatile_day            BOOLEAN,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, session_date)
);

CREATE INDEX IF NOT EXISTS idx_its_session_date
    ON intraday_training_sessions (session_date DESC);

CREATE INDEX IF NOT EXISTS idx_its_session_type
    ON intraday_training_sessions (session_type);
