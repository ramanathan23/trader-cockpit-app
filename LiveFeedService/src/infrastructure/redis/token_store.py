"""
TokenStore: Redis-backed Dhan credential store with env-var fallback.

Usage
-----
  store = TokenStore(redis_url, fallback_token="from-env")
  token = await store.get()         # read (Redis → fallback)
  await store.set("new-token")      # write (persists in Redis)
  await store.close()
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_KEY = "dhan:access_token"


class TokenStore:
    """
    Reads/writes the Dhan access token from Redis.

    On first start the token is seeded from the environment variable so
    existing deployments keep working without manual Redis setup.
    On subsequent starts or after a live update the Redis value takes
    precedence over the env var.
    """

    def __init__(self, redis_url: str, env_fallback: str) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._env_fallback = env_fallback

    async def seed_if_missing(self) -> None:
        """
        Write the env-var token to Redis only when no key exists yet.
        Call this once at startup so the first run needs no manual Redis step.
        """
        if self._env_fallback and not await self._redis.exists(_KEY):
            await self._redis.set(_KEY, self._env_fallback)
            logger.info("TokenStore: seeded dhan:access_token from env var")

    async def get(self) -> str:
        """Return the current token (Redis value, or env fallback if key absent)."""
        token = await self._redis.get(_KEY)
        if not token:
            logger.warning(
                "TokenStore: Redis key '%s' missing — falling back to env var", _KEY
            )
            return self._env_fallback
        return token

    async def set(self, token: str) -> None:
        """Persist a new token to Redis. Takes effect on next WS reconnect."""
        await self._redis.set(_KEY, token)
        logger.info("TokenStore: dhan:access_token updated in Redis")

    async def close(self) -> None:
        await self._redis.aclose()
