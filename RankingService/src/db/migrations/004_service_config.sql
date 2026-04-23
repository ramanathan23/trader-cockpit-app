-- Shared service_config table. Idempotent — safe to re-run on startup.

CREATE TABLE IF NOT EXISTS service_config (
    service     VARCHAR(50)  NOT NULL,
    key         VARCHAR(100) NOT NULL,
    value       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (service, key)
);

CREATE INDEX IF NOT EXISTS idx_service_config_service
    ON service_config (service);
