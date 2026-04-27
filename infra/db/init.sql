-- trader-cockpit-app: complete database schema.
-- Run by TimescaleDB container on first start (Docker entrypoint).
-- Each service also runs its own consolidated migration file on startup (idempotent).
--
-- Tables (by service):
--   DataSyncService : symbols, price_data_daily, price_data_1min, sync_state, index_futures
--   Shared          : service_config

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
-- Shared: service_config
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS service_config (
    service     VARCHAR(50)  NOT NULL,
    key         VARCHAR(100) NOT NULL,
    value       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (service, key)
);

CREATE INDEX IF NOT EXISTS idx_service_config_service
    ON service_config (service);
