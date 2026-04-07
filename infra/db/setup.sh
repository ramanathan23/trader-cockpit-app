#!/usr/bin/env sh
# Idempotent bootstrap for the local (host) PostgreSQL instance.
# Runs as a one-shot Docker service; connects via host.docker.internal.
# Required env vars (set in docker-compose / .env):
#   PGPASSWORD              — superuser password
#   PGUSER                  — superuser name  (default: postgres)
#   PGHOST                  — host            (default: host.docker.internal)
#   PGPORT                  — port            (default: 5432)
#   DB_USER, DB_PASSWORD, DB_NAME

set -eu

HOST="${PGHOST:-host.docker.internal}"
PORT="${PGPORT:-5432}"
SU="${PGUSER:-postgres}"
APP_USER="${DB_USER:-trader}"
APP_PASS="${DB_PASSWORD:-trader_secret}"
APP_DB="${DB_NAME:-trader_cockpit}"

psql() {
    command psql -h "$HOST" -p "$PORT" -U "$SU" "$@"
}

echo "==> Waiting for PostgreSQL at $HOST:$PORT ..."
until pg_isready -h "$HOST" -p "$PORT" -U "$SU" -q; do
    sleep 1
done
echo "    PostgreSQL is ready."

echo "==> Creating role '$APP_USER' (if not exists)..."
psql -d postgres -c "
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_USER}') THEN
    CREATE ROLE ${APP_USER} WITH LOGIN PASSWORD '${APP_PASS}';
    RAISE NOTICE 'Role % created', '${APP_USER}';
  ELSE
    RAISE NOTICE 'Role % already exists, skipping', '${APP_USER}';
  END IF;
END
\$\$;"

echo "==> Creating database '$APP_DB' (if not exists)..."
DB_EXISTS=$(psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${APP_DB}'")
if [ "$DB_EXISTS" = "1" ]; then
    echo "    Database '$APP_DB' already exists, skipping."
else
    psql -d postgres -c "CREATE DATABASE ${APP_DB} OWNER ${APP_USER};"
    echo "    Database '$APP_DB' created."
fi

echo "==> Granting privileges..."
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${APP_DB} TO ${APP_USER};"

echo "==> Enabling TimescaleDB extension in '$APP_DB'..."
if psql -d "$APP_DB" -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;" 2>&1; then
    echo "    TimescaleDB extension enabled."
else
    echo ""
    echo "  !! WARNING: TimescaleDB extension is NOT installed on the host PostgreSQL."
    echo "  !! Install it from: https://docs.timescale.com/self-hosted/latest/install/"
    echo "  !! (Use StackBuilder bundled with PostgreSQL, or the standalone Windows installer)"
    echo "  !! Service migrations WILL FAIL until TimescaleDB is installed and PG is restarted."
    echo ""
fi

echo "==> Done. Database setup complete."
