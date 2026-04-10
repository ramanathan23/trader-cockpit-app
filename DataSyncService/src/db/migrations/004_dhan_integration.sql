-- Dhan integration: add security ID mapping to symbols table.
-- Idempotent — safe to re-run on every startup.

ALTER TABLE symbols
    ADD COLUMN IF NOT EXISTS dhan_security_id  BIGINT,
    ADD COLUMN IF NOT EXISTS exchange_segment  VARCHAR(20);
    -- exchange_segment values: NSE_EQ | BSE_EQ | NSE_FNO | BSE_FNO | IDX_I

CREATE INDEX IF NOT EXISTS idx_symbols_dhan_id
    ON symbols(dhan_security_id)
    WHERE dhan_security_id IS NOT NULL;

-- Index futures used as intraday market proxy (NIFTY / BANKNIFTY / SENSEX).
-- One active row per underlying per expiry; is_active=TRUE marks the front month.
CREATE TABLE IF NOT EXISTS index_futures (
    id                SERIAL        PRIMARY KEY,
    underlying        VARCHAR(20)   NOT NULL,        -- 'NIFTY' | 'BANKNIFTY' | 'SENSEX'
    dhan_security_id  BIGINT        NOT NULL,
    exchange_segment  VARCHAR(20)   NOT NULL,        -- 'NSE_FNO' | 'BSE_FNO'
    lot_size          INTEGER       NOT NULL DEFAULT 1,
    expiry_date       DATE          NOT NULL,
    is_active         BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_index_futures_underlying_expiry UNIQUE (underlying, expiry_date)
);

CREATE INDEX IF NOT EXISTS idx_index_futures_active
    ON index_futures(underlying)
    WHERE is_active = TRUE;
