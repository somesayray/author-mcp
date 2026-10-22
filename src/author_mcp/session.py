"""Session Management and Caching backed by Redis (Author-Sessions container)."""

from __future__ import annotations

import json
from typing import Any
import redis.asyncio as redis
import structlog

from author_mcp.config import settings

logger = structlog.get_logger(__name__)


class SessionManager:
    """Manages session cache and ephemeral memory using the Author-Sessions Redis container."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def ping(self) -> bool:
        """Check connection to Author-Sessions Redis."""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception as e:
            logger.warning("redis_session_ping_failed", error=str(e), url=self.redis_url)
            return False

    async def set_value(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        try:
            client = await self.get_client()
            serialized = json.dumps(value) if not isinstance(value, str) else value
            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized)
            else:
                await client.set(key, serialized)
            return True
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False

    async def get_value(self, key: str) -> Any:
        try:
            client = await self.get_client()
            val = await client.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except Exception:
                return val
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None

    async def delete_value(self, key: str) -> bool:
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
