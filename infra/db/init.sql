-- trader-cockpit-app: complete database schema.
-- Run by TimescaleDB container on first start (Docker entrypoint).
-- Each service also runs its own consolidated migration file on startup (idempotent).
--
-- Tables (by service):
--   DataSyncService  : symbols, price_data_daily, sync_state, index_futures,
--                      symbol_metrics, price_daily_weekly, price_daily_monthly,
--                      price_data_1min
--   MomentumScorer   : daily_scores
--   LiveFeedService  : candles_5min, index_future_candles_5min
--   ModelingService  : model_predictions

-- ── Extensions ────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ═══════════════════════════════════════════════════════════════════════════════
-- DataSyncService
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS symbols (
    symbol            VARCHAR(30) PRIMARY KEY,
    company_name      TEXT        NOT NULL,
    series            VARCHAR(10) NOT NULL DEFAULT 'EQ',
    isin              VARCHAR(20),
    listed_date       DATE,
    face_value        NUMERIC(10,2),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dhan_security_id  BIGINT,
    exchange_segment  VARCHAR(20),
    is_fno            BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_symbols_series
    ON symbols(series);

CREATE INDEX IF NOT EXISTS idx_symbols_dhan_id
    ON symbols(dhan_security_id)
    WHERE dhan_security_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_symbols_is_fno
    ON symbols(is_fno)
    WHERE is_fno = TRUE;

-- ── price_data_daily ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS price_data_daily (
    time    TIMESTAMPTZ NOT NULL,
    symbol  VARCHAR(30) NOT NULL,
    open    NUMERIC(14,4),
    high    NUMERIC(14,4),
    low     NUMERIC(14,4),
    close   NUMERIC(14,4),
    volume  BIGINT,
    CONSTRAINT pk_price_daily PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'price_data_daily', 'time',
    partitioning_column    => 'symbol',
    number_partitions      => 8,
    chunk_time_interval    => INTERVAL '1 month',
    create_default_indexes => FALSE,
    if_not_exists          => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_daily_time_desc
    ON price_data_daily (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_daily_symbol_time_desc
    ON price_data_daily (symbol, time DESC);

ALTER TABLE price_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy(
    'price_data_daily',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ── sync_state ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sync_state (
    symbol         VARCHAR(30) NOT NULL,
    timeframe      VARCHAR(10) NOT NULL,
    last_synced_at TIMESTAMPTZ,
    last_data_ts   TIMESTAMPTZ,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_msg      TEXT,
    CONSTRAINT pk_sync_state PRIMARY KEY (symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_status
    ON sync_state(status);

CREATE INDEX IF NOT EXISTS idx_sync_state_last_synced
    ON sync_state(last_synced_at ASC NULLS FIRST);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_symbol
    ON sync_state(timeframe, symbol);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_last_data
    ON sync_state(timeframe, last_data_ts ASC NULLS FIRST);

CREATE INDEX IF NOT EXISTS idx_sync_state_timeframe_last_synced
    ON sync_state(timeframe, last_synced_at ASC NULLS FIRST);

-- ── index_futures ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS index_futures (
    id                SERIAL      PRIMARY KEY,
    underlying        VARCHAR(20) NOT NULL,
    dhan_security_id  BIGINT      NOT NULL,
    exchange_segment  VARCHAR(20) NOT NULL,
    lot_size          INTEGER     NOT NULL DEFAULT 1,
    expiry_date       DATE        NOT NULL,
    is_active         BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_index_futures_underlying_expiry UNIQUE (underlying, expiry_date)
);

CREATE INDEX IF NOT EXISTS idx_index_futures_active
    ON index_futures(underlying)
    WHERE is_active = TRUE;

-- ── symbol_metrics ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS symbol_metrics (
    symbol             VARCHAR(30) PRIMARY KEY,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 52-week range + core metrics
    week52_high        NUMERIC(14,4),
    week52_low         NUMERIC(14,4),
    atr_14             NUMERIC(14,4),
    adv_20_cr          NUMERIC(10,2),
    trading_days       INTEGER,
    -- prior period OHLC
    prev_day_high      NUMERIC(14,4),
    prev_day_low       NUMERIC(14,4),
    prev_day_close     NUMERIC(14,4),
    prev_week_high     NUMERIC(14,4),
    prev_week_low      NUMERIC(14,4),
    prev_month_high    NUMERIC(14,4),
    prev_month_low     NUMERIC(14,4),
    -- trend
    ema_50             NUMERIC(14,4),
    ema_200            NUMERIC(14,4),
    -- weekly performance
    week_return_pct    NUMERIC(9,4),
    week_gain_pct      NUMERIC(9,4),
    week_decline_pct   NUMERIC(9,4),
    -- volatility compression (extended)
    atr_5              NUMERIC(14,4),
    adx_14             NUMERIC(6,2),
    plus_di            NUMERIC(6,2),
    minus_di           NUMERIC(6,2),
    bb_width           NUMERIC(10,6),
    kc_width           NUMERIC(10,6),
    bb_squeeze         BOOLEAN      DEFAULT FALSE,
    squeeze_days       INTEGER      DEFAULT 0,
    nr7                BOOLEAN      DEFAULT FALSE,
    atr_ratio          NUMERIC(6,4),
    -- momentum indicators
    rsi_14             NUMERIC(6,2),
    macd_hist          NUMERIC(12,4),
    roc_5              NUMERIC(9,4),
    roc_20             NUMERIC(9,4),
    roc_60             NUMERIC(9,4),
    vol_ratio_20       NUMERIC(6,2),
    rs_vs_nifty        NUMERIC(9,4),
    weekly_bias        VARCHAR(10)  DEFAULT 'NEUTRAL'
);

CREATE INDEX IF NOT EXISTS idx_symbol_metrics_computed_at
    ON symbol_metrics (computed_at DESC);

-- ── Continuous aggregates ─────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', time) AS bucket,
    symbol,
    FIRST(open, time)           AS open,
    MAX(high)                   AS high,
    MIN(low)                    AS low,
    LAST(close, time)           AS close,
    SUM(volume)                 AS volume
FROM price_data_daily
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_daily_weekly',
    start_offset      => INTERVAL '1 month',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists     => TRUE
);

CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily_monthly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', time) AS bucket,
    symbol,
    FIRST(open, time)            AS open,
    MAX(high)                    AS high,
    MIN(low)                     AS low,
    LAST(close, time)            AS close,
    SUM(volume)                  AS volume
FROM price_data_daily
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'price_daily_monthly',
    start_offset      => INTERVAL '3 months',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists     => TRUE
);

-- ── price_data_1min ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS price_data_1min (
    time    TIMESTAMPTZ NOT NULL,
    symbol  VARCHAR(30) NOT NULL,
    open    NUMERIC(10,4),
    high    NUMERIC(10,4),
    low     NUMERIC(10,4),
    close   NUMERIC(10,4),
    volume  BIGINT,
    CONSTRAINT pk_price_1min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'price_data_1min', 'time',
    partitioning_column    => 'symbol',
    number_partitions      => 4,
    chunk_time_interval    => INTERVAL '1 week',
    create_default_indexes => FALSE,
    if_not_exists          => TRUE
);

CREATE INDEX IF NOT EXISTS idx_price_1min_time_desc
    ON price_data_1min (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_1min_symbol_time_desc
    ON price_data_1min (symbol, time DESC);

ALTER TABLE price_data_1min SET (
    timescaledb.compress,
    timescaledb.compress_orderby   = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy(
    'price_data_1min',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ── F&O universe seed ─────────────────────────────────────────────────────────

UPDATE symbols SET is_fno = FALSE WHERE is_fno = TRUE;

UPDATE symbols
SET    is_fno = TRUE
WHERE  symbol IN (
    '360ONE', 'ABB', 'APLAPOLLO', 'AUBANK', 'ADANIENSOL', 'ADANIENT',
    'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ABCAPITAL', 'ALKEM', 'AMBER',
    'AMBUJACEM', 'ANGELONE', 'APOLLOHOSP', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL',
    'AUROPHARMA', 'DMART', 'AXISBANK', 'BSE', 'BAJAJ-AUTO', 'BAJFINANCE',
    'BAJAJFINSV', 'BAJAJHLDNG', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BDL',
    'BEL', 'BHARATFORG', 'BHEL', 'BPCL', 'BHARTIARTL', 'BIOCON', 'BLUESTARCO',
    'BOSCHLTD', 'BRITANNIA', 'CGPOWER', 'CANBK', 'CDSL', 'CHOLAFIN', 'CIPLA',
    'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COLPAL', 'CAMS', 'CONCOR',
    'CROMPTON', 'CUMMINSIND', 'DLF', 'DABUR', 'DALBHARAT', 'DELHIVERY',
    'DIVISLAB', 'DIXON', 'DRREDDY', 'ETERNAL', 'EICHERMOT', 'EXIDEIND',
    'FORCEMOT', 'NYKAA', 'FORTIS', 'GAIL', 'GMRAIRPORT', 'GLENMARK',
    'GODFRYPHLP', 'GODREJCP', 'GODREJPROP', 'GRASIM', 'HCLTECH', 'HDFCAMC',
    'HDFCBANK', 'HDFCLIFE', 'HAVELLS', 'HEROMOTOCO', 'HINDALCO', 'HAL',
    'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'POWERINDIA', 'HUDCO', 'HYUNDAI',
    'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDFCFIRSTB', 'ITC', 'INDIANB',
    'IEX', 'IOC', 'IRFC', 'IREDA', 'INDUSTOWER', 'INDUSINDBK', 'NAUKRI',
    'INFY', 'INOXWIND', 'INDIGO', 'JINDALSTEL', 'JSWENERGY', 'JSWSTEEL',
    'JIOFIN', 'JUBLFOOD', 'KEI', 'KPITTECH', 'KALYANKJIL', 'KAYNES',
    'KFINTECH', 'KOTAKBANK', 'LTF', 'LICHSGFIN', 'LTM', 'LT', 'LAURUSLABS',
    'LICI', 'LODHA', 'LUPIN', 'M&M', 'MANAPPURAM', 'MANKIND', 'MARICO',
    'MARUTI', 'MFSL', 'MAXHEALTH', 'MAZDOCK', 'MOTILALOFS', 'MPHASIS', 'MCX',
    'MUTHOOTFIN', 'NBCC', 'NHPC', 'NMDC', 'NTPC', 'NATIONALUM', 'NESTLEIND',
    'NAM-INDIA', 'NUVAMA', 'OBEROIRLTY', 'ONGC', 'OIL', 'PAYTM', 'OFSS',
    'POLICYBZR', 'PGEL', 'PIIND', 'PNBHOUSING', 'PAGEIND', 'PATANJALI',
    'PERSISTENT', 'PETRONET', 'PIDILITIND', 'PPLPHARMA', 'POLYCAB', 'PFC',
    'POWERGRID', 'PREMIERENE', 'PRESTIGE', 'PNB', 'RBLBANK', 'RECLTD', 'RVNL',
    'RELIANCE', 'SBICARD', 'SBILIFE', 'SHREECEM', 'SRF', 'SAMMAANCAP',
    'MOTHERSON', 'SHRIRAMFIN', 'SIEMENS', 'SOLARINDS', 'SONACOMS', 'SBIN',
    'SAIL', 'SUNPHARMA', 'SUPREMEIND', 'SUZLON', 'SWIGGY', 'TATACONSUM',
    'TVSMOTOR', 'TCS', 'TATAELXSI', 'TMPV', 'TATAPOWER', 'TATASTEEL',
    'TATATECH', 'TECHM', 'FEDERALBNK', 'INDHOTEL', 'PHOENIXLTD', 'TITAN',
    'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TIINDIA', 'UNOMINDA', 'UPL',
    'ULTRACEMCO', 'UNIONBANK', 'UNITDSPR', 'VBL', 'VEDL', 'VMM', 'IDEA',
    'VOLTAS', 'WAAREEENER', 'WIPRO', 'YESBANK', 'ZYDUSLIFE'
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- MomentumScorerService
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── daily_scores ──────────────────────────────────────────────────────────────
-- Unified scoring table. Replaces the legacy momentum_scores table.
-- Includes all indicator columns for historical ML feature retrieval (no JOIN needed).

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
    comfort_score       NUMERIC(6,2),
    -- Embedded indicator snapshot (eliminates look-ahead bias in ML training)
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

CREATE INDEX IF NOT EXISTS idx_daily_scores_comfort
    ON daily_scores (score_date DESC, comfort_score DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- LiveFeedService
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── candles_5min ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candles_5min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(30)    NOT NULL,
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_candles_5min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'candles_5min', 'time',
    partitioning_column => 'symbol',
    number_partitions   => 16,
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_candles_5min_symbol_time
    ON candles_5min (symbol, time DESC);

-- ── index_future_candles_5min ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS index_future_candles_5min (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      VARCHAR(20)    NOT NULL,
    open        NUMERIC(14,4)  NOT NULL,
    high        NUMERIC(14,4)  NOT NULL,
    low         NUMERIC(14,4)  NOT NULL,
    close       NUMERIC(14,4)  NOT NULL,
    volume      BIGINT         NOT NULL DEFAULT 0,
    tick_count  INTEGER        NOT NULL DEFAULT 0,
    CONSTRAINT pk_idx_fut_candles_5min PRIMARY KEY (symbol, time)
);

SELECT create_hypertable(
    'index_future_candles_5min', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_fut_candles_5min_symbol_time
    ON index_future_candles_5min (symbol, time DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ModelingService
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── model_predictions ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_predictions (
    id               BIGSERIAL    PRIMARY KEY,
    model_name       TEXT         NOT NULL,
    model_version    TEXT         NOT NULL,
    symbol           TEXT         NOT NULL,
    prediction_date  DATE         NOT NULL,
    predictions      JSONB        NOT NULL,
    confidence       REAL,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (model_name, symbol, prediction_date)
);

CREATE INDEX IF NOT EXISTS idx_predictions_model
    ON model_predictions(model_name, prediction_date DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol
    ON model_predictions(symbol, prediction_date DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_created
    ON model_predictions(created_at DESC);
