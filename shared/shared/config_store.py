"""
Runtime config store — reads/writes service_config table in Postgres.

On startup: load_overrides() → apply_overrides() patches settings singleton.
On admin PATCH: save_overrides() persists + caller applies immediately.
"""

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

# Fields that must never be exposed or overwritten via admin config.
_EXCLUDED: frozenset[str] = frozenset({
    "database_url", "redis_url", "log_level",
    "db_pool_min_size", "db_pool_max_size", "db_command_timeout",
    "db_migration_timeout", "db_metrics_recompute_timeout",
    "dhan_client_id", "dhan_access_token",
    "dhan_master_url", "dhan_historical_url",
    "modeling_service_url",
    "model_base_path",
})


def get_tunable(settings: Any) -> dict[str, Any]:
    """Return all settings fields that are safe to expose and edit."""
    return {
        k: v for k, v in settings.model_dump().items()
        if k not in _EXCLUDED
    }


def _coerce(settings: Any, key: str, value: Any) -> Any:
    """Coerce value to match the annotated field type on settings."""
    fields = settings.model_fields
    if key not in fields:
        raise KeyError(f"unknown field: {key}")
    ann = fields[key].annotation
    if ann is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    if ann is int:
        return int(value)
    if ann is float:
        return float(value)
    if ann is str:
        return str(value)
    return value


async def load_overrides(pool: asyncpg.Pool, service: str) -> dict[str, Any]:
    """Fetch all config overrides for *service* from DB."""
    rows = await pool.fetch(
        "SELECT key, value FROM service_config WHERE service = $1", service
    )
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except Exception:
            result[row["key"]] = row["value"]
    return result


def apply_overrides(settings: Any, overrides: dict[str, Any]) -> None:
    """Apply DB overrides onto settings singleton in-place."""
    for key, value in overrides.items():
        if key in _EXCLUDED or not hasattr(settings, key):
            continue
        try:
            coerced = _coerce(settings, key, value)
            object.__setattr__(settings, key, coerced)
            logger.info("Config override applied: %s = %r", key, coerced)
        except Exception as exc:
            logger.warning("Skipped config override %s=%r: %s", key, value, exc)


async def save_overrides(
    pool: asyncpg.Pool, service: str, updates: dict[str, Any]
) -> None:
    """Upsert config overrides for *service* into DB."""
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO service_config (service, key, value, updated_at)
            VALUES ($1, $2, $3::jsonb, NOW())
            ON CONFLICT (service, key) DO UPDATE
              SET value = EXCLUDED.value, updated_at = NOW()
            """,
            [(service, k, json.dumps(v)) for k, v in updates.items()],
        )
