"""Puerto de cache (out)."""

from __future__ import annotations

from typing import Protocol


class ICacheGateway(Protocol):
    def get(self, key: str) -> str | None: ...

    def put(self, key: str, value: str, ttl_seconds: int) -> bool: ...

    def evict(self, key: str) -> bool: ...
