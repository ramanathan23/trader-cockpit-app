CREATE TABLE IF NOT EXISTS symbol_intraday_profile (
    symbol                       VARCHAR(30) PRIMARY KEY REFERENCES symbols(symbol),
    computed_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sessions_analyzed            INTEGER     NOT NULL DEFAULT 0,
    choppiness_idx               NUMERIC(8,4),
    stop_hunt_rate               NUMERIC(6,4),
    orb_followthrough_rate       NUMERIC(6,4),
    opening_drive_rate           NUMERIC(6,4),
    pullback_depth_on_up_days    NUMERIC(6,4),
    volatility_compression_ratio NUMERIC(8,4),
    trend_autocorr               NUMERIC(8,4),
    iss_score                    NUMERIC(6,2)
);

CREATE INDEX IF NOT EXISTS idx_intraday_profile_computed
    ON symbol_intraday_profile (computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_intraday_profile_iss
    ON symbol_intraday_profile (iss_score DESC);
