"""Cache remoto (Redis) con TTL obligatorio y DEGRADACION.

Si Redis falla, el cache no rompe el flujo de negocio (get -> None, put -> False).
El caller sigue a la fuente de verdad (PERF-BP + RES-O-005). El cliente Redis se
inyecta (Protocol) para no acoplar el arquetipo a un driver concreto ni forzar la
dependencia en el cold path.
"""

from __future__ import annotations

from typing import Protocol

from accounts.domain.ports.cache import ICacheGateway
from accounts.infrastructure.helpers.observability import logger


class RedisLikeClient(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ex: int) -> object: ...

    def delete(self, key: str) -> int: ...


class RedisCacheGateway(ICacheGateway):
    def __init__(self, client: RedisLikeClient) -> None:
        self._client = client

    def get(self, key: str) -> str | None:
        try:
            return self._client.get(key)
        except Exception as e:
            logger.warning(
                "cache get fallo; se degrada a miss", extra={"key": key, "error": str(e)}
            )
            return None

    def put(self, key: str, value: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("TTL is mandatory and must be positive")
        try:
            self._client.set(key, value, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning(
                "cache put fallo; se ignora (degradacion)", extra={"key": key, "error": str(e)}
            )
            return False

    def evict(self, key: str) -> bool:
        try:
            return self._client.delete(key) > 0
        except Exception:
            return False
