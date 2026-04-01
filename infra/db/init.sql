-- Runs once on TimescaleDB container first start.
-- Enables the extension; schema DDL is applied by each service on startup.
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
