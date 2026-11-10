from __future__ import annotations

import pytest

from accounts.infrastructure.driven_adapters.rds.connection_pool import (
    SqlConnectionPool,
    _reset_pool_for_test,
    get_pool,
)


class StubPool(SqlConnectionPool):
    def query(self, sql: str, params: tuple[object, ...] | None = None) -> list[dict[str, object]]:
        return []

    def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _reset() -> None:
    _reset_pool_for_test()


def test_crea_pool_con_max_size_1() -> None:
    seen: dict[str, object] = {}

    def factory(*, host: str, database: str, max_size: int) -> SqlConnectionPool:
        seen.update({"host": host, "database": database, "max_size": max_size})
        return StubPool()

    get_pool(factory, host="h", database="d")
    assert seen == {"host": "h", "database": "d", "max_size": 1}


def test_reutiliza_singleton() -> None:
    calls = 0

    def factory(*, host: str, database: str, max_size: int) -> SqlConnectionPool:
        nonlocal calls
        calls += 1
        return StubPool()

    a = get_pool(factory, host="h", database="d")
    b = get_pool(factory, host="h", database="d")
    assert a is b
    assert calls == 1


def test_reset_fuerza_recreacion() -> None:
    calls = 0

    def factory(*, host: str, database: str, max_size: int) -> SqlConnectionPool:
        nonlocal calls
        calls += 1
        return StubPool()

    get_pool(factory, host="h", database="d")
    _reset_pool_for_test()
    get_pool(factory, host="h", database="d")
    assert calls == 2
