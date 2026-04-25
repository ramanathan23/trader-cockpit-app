CREATE TABLE IF NOT EXISTS broker_pnl_statement (
    broker          VARCHAR(20) NOT NULL,
    account_id      VARCHAR(80) NOT NULL,
    row_hash        VARCHAR(80) NOT NULL,
    statement_date  DATE,
    trading_symbol  VARCHAR(120),
    segment         VARCHAR(40),
    realized_pnl    NUMERIC(18,4) NOT NULL DEFAULT 0,
    charges         NUMERIC(18,4) NOT NULL DEFAULT 0,
    net_realized_pnl NUMERIC(18,4) NOT NULL DEFAULT 0,
    payload         JSONB NOT NULL,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_broker_pnl_statement PRIMARY KEY (broker, account_id, row_hash)
);

CREATE INDEX IF NOT EXISTS idx_broker_pnl_account_date
    ON broker_pnl_statement (broker, account_id, statement_date DESC);
