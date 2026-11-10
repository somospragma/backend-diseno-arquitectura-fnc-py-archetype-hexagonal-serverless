from __future__ import annotations

import pytest

from accounts.infrastructure.driven_adapters.cache.redis_cache_gateway import RedisCacheGateway


class FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self._store: dict[str, str] = {}
        self._fail = fail

    def get(self, key: str) -> str | None:
        if self._fail:
            raise RuntimeError("down")
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int) -> object:
        if self._fail:
            raise RuntimeError("down")
        self._store[key] = value
        return "OK"

    def delete(self, key: str) -> int:
        if self._fail:
            raise RuntimeError("down")
        return 1 if self._store.pop(key, None) is not None else 0


def test_get_hit_y_miss() -> None:
    gw = RedisCacheGateway(FakeRedis())
    assert gw.get("k") is None
    gw.put("k", "v", 60)
    assert gw.get("k") == "v"


def test_get_degrada_a_none_si_falla() -> None:
    assert RedisCacheGateway(FakeRedis(fail=True)).get("k") is None


def test_put_ttl_obligatorio() -> None:
    gw = RedisCacheGateway(FakeRedis())
    with pytest.raises(ValueError, match="TTL is mandatory"):
        gw.put("k", "v", 0)
    with pytest.raises(ValueError, match="TTL is mandatory"):
        gw.put("k", "v", -1)


def test_put_degrada_a_false_si_falla() -> None:
    assert RedisCacheGateway(FakeRedis(fail=True)).put("k", "v", 60) is False


def test_evict() -> None:
    gw = RedisCacheGateway(FakeRedis())
    gw.put("k", "v", 60)
    assert gw.evict("k") is True
    assert gw.evict("k") is False
    assert RedisCacheGateway(FakeRedis(fail=True)).evict("k") is False
