"""Modelo de dominio Account.

Tipos planos, sin dependencias de framework ni de infraestructura (hexagonal: el
dominio no conoce AWS, DynamoDB ni handlers). Se usan dataclasses puras para no
acoplar el nucleo a Pydantic (la validacion de entrada vive en el borde HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class Account:
    """Entidad de dominio. Inmutable: las mutaciones devuelven una copia."""

    id: str
    holder_name: str
    # Dato sensible (PII): se enmascara en logs y respuestas.
    email: str
    account_type: str
    balance: float
    status: AccountStatus
    created_at: str  # ISO-8601

    def with_changes(self, **changes: object) -> Account:
        """Devuelve una copia con los cambios aplicados (sin mutar el original)."""
        return replace(self, **changes)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class AccountSearchCriteria:
    """Criterios de busqueda (campos None no filtran)."""

    status: AccountStatus | None = None
    account_type: str | None = None
    holder_name: str | None = None


@dataclass(frozen=True, slots=True)
class AccountEvent:
    """Evento de cuenta (publicacion a SNS/EventBridge)."""

    account_id: str
    event_id: str
    type: str
    occurred_at: str  # ISO-8601
