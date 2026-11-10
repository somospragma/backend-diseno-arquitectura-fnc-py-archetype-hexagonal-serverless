"""Casos de uso de cuentas.

Clases planas framework-free: sin imports de AWS, infra ni handlers. Reciben el
puerto por constructor (inyeccion). La capa de composicion (application) los cablea
con los adapters concretos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from accounts.domain.model.account import (
    Account,
    AccountSearchCriteria,
    AccountStatus,
)
from accounts.domain.model.errors import AccountNotFoundError
from accounts.domain.ports.account_repository import IAccountRepository

MAX_LIMIT = 100


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class CreateAccountInput:
    holder_name: str
    email: str
    account_type: str
    initial_balance: float


@dataclass(frozen=True, slots=True)
class ReplaceAccountInput:
    holder_name: str
    email: str
    account_type: str
    balance: float
    status: AccountStatus


@dataclass(frozen=True, slots=True)
class PatchAccountInput:
    holder_name: str | None = None
    email: str | None = None
    account_type: str | None = None
    status: AccountStatus | None = None
    balance: float | None = None


class CreateAccountUseCase:
    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, data: CreateAccountInput) -> Account:
        account = Account(
            id=str(uuid.uuid4()),
            holder_name=data.holder_name,
            email=data.email,
            account_type=data.account_type,
            balance=data.initial_balance,
            status=AccountStatus.ACTIVE,
            created_at=_now_iso(),
        )
        return self._repo.save(account)


class GetAccountUseCase:
    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, account_id: str) -> Account:
        found = self._repo.find_by_id(account_id)
        if found is None:
            raise AccountNotFoundError(account_id)
        return found


class UpdateAccountUseCase:
    """Reemplazo total (PUT), idempotente. Preserva id y created_at del existente."""

    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, account_id: str, replacement: ReplaceAccountInput) -> Account:
        existing = self._repo.find_by_id(account_id)
        if existing is None:
            raise AccountNotFoundError(account_id)
        updated = Account(
            id=existing.id,
            holder_name=replacement.holder_name,
            email=replacement.email,
            account_type=replacement.account_type,
            balance=replacement.balance,
            status=replacement.status,
            created_at=existing.created_at,
        )
        return self._repo.save(updated)


class PatchAccountUseCase:
    """Actualizacion parcial (PATCH): solo aplica los campos presentes."""

    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, account_id: str, patch: PatchAccountInput) -> Account:
        existing = self._repo.find_by_id(account_id)
        if existing is None:
            raise AccountNotFoundError(account_id)
        changes: dict[str, object] = {}
        if patch.holder_name is not None:
            changes["holder_name"] = patch.holder_name
        if patch.email is not None:
            changes["email"] = patch.email
        if patch.account_type is not None:
            changes["account_type"] = patch.account_type
        if patch.status is not None:
            changes["status"] = patch.status
        if patch.balance is not None:
            changes["balance"] = patch.balance
        return self._repo.save(existing.with_changes(**changes))


class DeleteAccountUseCase:
    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, account_id: str) -> None:
        if not self._repo.exists_by_id(account_id):
            raise AccountNotFoundError(account_id)
        self._repo.delete_by_id(account_id)


class SearchAccountsUseCase:
    """Busqueda con tope duro: nunca colecciones ilimitadas (API-O-005)."""

    def __init__(self, repo: IAccountRepository) -> None:
        self._repo = repo

    def execute(self, criteria: AccountSearchCriteria, limit: int = 20) -> list[Account]:
        capped = min(max(limit, 1), MAX_LIMIT)
        return self._repo.search(criteria, capped)
