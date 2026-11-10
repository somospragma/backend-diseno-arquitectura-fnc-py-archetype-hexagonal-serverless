"""Conexion a BD relacional consciente del modelo Lambda (SRV-O-005).

Regla: pool con max=1 CREADO FUERA del handler (a nivel de modulo) y reutilizado
entre invocaciones en el mismo contenedor caliente. Alternativas validas: RDS Proxy
o Data API. Nunca abrir/cerrar conexion por invocacion.

Aqui se modela el contrato (Protocol) y una fabrica; el driver real (p.ej.
psycopg) se inyecta para no acoplar el arquetipo a un motor concreto ni forzar la
dependencia en el bundle.
"""

from __future__ import annotations

from typing import Protocol


class SqlConnectionPool(Protocol):
    def query(
        self, sql: str, params: tuple[object, ...] | None = None
    ) -> list[dict[str, object]]: ...

    def close(self) -> None: ...


class PoolFactory(Protocol):
    def __call__(self, *, host: str, database: str, max_size: int) -> SqlConnectionPool: ...


_cached_pool: SqlConnectionPool | None = None


def get_pool(factory: PoolFactory, *, host: str, database: str) -> SqlConnectionPool:
    """Devuelve un pool singleton (max=1) reutilizado entre invocaciones.

    El pool se crea una sola vez por contenedor (cold start) y se reutiliza en
    warm starts. max_size=1: consciente de Lambda.
    """
    global _cached_pool  # noqa: PLW0603 - singleton por contenedor Lambda (SRV-O-005)
    if _cached_pool is None:
        _cached_pool = factory(host=host, database=database, max_size=1)
    return _cached_pool


def _reset_pool_for_test() -> None:
    """Visible para test: resetea el singleton."""
    global _cached_pool  # noqa: PLW0603 - reset del singleton en pruebas
    _cached_pool = None
