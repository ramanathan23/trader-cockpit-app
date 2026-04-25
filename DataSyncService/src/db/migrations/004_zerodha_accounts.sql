CREATE TABLE IF NOT EXISTS broker_accounts (
    id              SERIAL PRIMARY KEY,
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    client_id       VARCHAR(80),
    display_name    VARCHAR(120),
    api_key         TEXT,
    api_secret      TEXT,
    strategy_capital NUMERIC(18,2),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_broker_account UNIQUE (broker, account_id)
);

ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS api_key TEXT;
ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS api_secret TEXT;
ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS strategy_capital NUMERIC(18,2);

CREATE TABLE IF NOT EXISTS broker_tokens (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    access_token    TEXT,
    public_token    TEXT,
    user_id         VARCHAR(80),
    user_name       TEXT,
    login_time      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    last_error      TEXT,
    raw_payload     JSONB,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_tokens PRIMARY KEY (broker, account_id)
);

CREATE TABLE IF NOT EXISTS broker_orders_raw (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    order_id        VARCHAR(80) NOT NULL,
    trading_symbol  VARCHAR(120),
    exchange        VARCHAR(20),
    status          VARCHAR(40),
    order_timestamp TIMESTAMPTZ,
    payload         JSONB NOT NULL,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_orders_raw PRIMARY KEY (broker, account_id, order_id)
);

CREATE TABLE IF NOT EXISTS broker_trades_raw (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    trade_id        VARCHAR(80) NOT NULL,
    order_id        VARCHAR(80),
    trading_symbol  VARCHAR(120),
    exchange        VARCHAR(20),
    transaction_type VARCHAR(10),
    quantity        NUMERIC(18,4),
    average_price   NUMERIC(18,4),
    fill_timestamp  TIMESTAMPTZ,
    payload         JSONB NOT NULL,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_trades_raw PRIMARY KEY (broker, account_id, trade_id)
);

CREATE TABLE IF NOT EXISTS broker_positions_raw (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    snapshot_date   DATE NOT NULL,
    payload         JSONB NOT NULL,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_positions_raw PRIMARY KEY (broker, account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS broker_holdings_raw (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    snapshot_date   DATE NOT NULL,
    payload         JSONB NOT NULL,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_holdings_raw PRIMARY KEY (broker, account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS broker_margins_raw (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    snapshot_date   DATE NOT NULL,
    payload         JSONB NOT NULL,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_margins_raw PRIMARY KEY (broker, account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS broker_sync_runs (
    id              BIGSERIAL PRIMARY KEY,
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    orders_count    INTEGER NOT NULL DEFAULT 0,
    trades_count    INTEGER NOT NULL DEFAULT 0,
    error_msg       TEXT
);

CREATE INDEX IF NOT EXISTS idx_broker_trades_account_time
    ON broker_trades_raw (broker, account_id, fill_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_broker_orders_account_time
    ON broker_orders_raw (broker, account_id, order_timestamp DESC);
