"""Puerto de persistencia de cuentas (out).

Definido como Protocol: el dominio declara QUE necesita; la infraestructura provee
el COMO. Sin herencia obligatoria ni imports de infraestructura.
"""

from __future__ import annotations

from typing import Protocol

from accounts.domain.model.account import Account, AccountSearchCriteria


class IAccountRepository(Protocol):
    def save(self, account: Account) -> Account: ...

    def find_by_id(self, account_id: str) -> Account | None: ...

    def exists_by_id(self, account_id: str) -> bool: ...

    def delete_by_id(self, account_id: str) -> None: ...

    def search(self, criteria: AccountSearchCriteria, limit: int) -> list[Account]: ...
