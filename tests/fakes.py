"""Dobles de prueba reutilizables (fakes en memoria)."""

from __future__ import annotations

from accounts.domain.model.account import Account, AccountSearchCriteria
from accounts.domain.ports.account_repository import IAccountRepository


class InMemoryAccountRepository(IAccountRepository):
    """Repositorio en memoria para probar los use cases sin infraestructura."""

    def __init__(self) -> None:
        self._data: dict[str, Account] = {}

    def save(self, account: Account) -> Account:
        self._data[account.id] = account
        return account

    def find_by_id(self, account_id: str) -> Account | None:
        return self._data.get(account_id)

    def exists_by_id(self, account_id: str) -> bool:
        return account_id in self._data

    def delete_by_id(self, account_id: str) -> None:
        self._data.pop(account_id, None)

    def search(self, criteria: AccountSearchCriteria, limit: int) -> list[Account]:
        result = list(self._data.values())
        if criteria.status is not None:
            result = [a for a in result if a.status == criteria.status]
        if criteria.account_type is not None:
            result = [a for a in result if a.account_type == criteria.account_type]
        if criteria.holder_name is not None:
            result = [a for a in result if a.holder_name == criteria.holder_name]
        return result[:limit]
