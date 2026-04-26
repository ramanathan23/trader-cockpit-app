CREATE TABLE IF NOT EXISTS intraday_session_predictions (
    symbol                  VARCHAR(30) NOT NULL,
    prediction_date         DATE        NOT NULL,
    session_type_pred       VARCHAR(15),
    trend_up_prob           NUMERIC(6,4),
    trend_down_prob         NUMERIC(6,4),
    chop_prob               NUMERIC(6,4),
    volatile_prob           NUMERIC(6,4),
    pullback_depth_pred     NUMERIC(6,4),
    model_version           VARCHAR(20) NOT NULL DEFAULT 'session_v1',
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, prediction_date)
);

CREATE INDEX IF NOT EXISTS idx_isp_date
    ON intraday_session_predictions (prediction_date DESC);
