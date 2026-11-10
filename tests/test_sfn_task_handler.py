from __future__ import annotations

import pytest

from accounts.domain.model.account import Account, AccountStatus
from accounts.domain.model.errors import AccountNotFoundError
from accounts.domain.usecases.account_usecases import GetAccountUseCase
from accounts.infrastructure.entry_points.handlers.sfn_task_handler import (
    SfnDeps,
    process_sfn_task,
)
from tests.fakes import InMemoryAccountRepository

ACC = Account(
    id="acc-1",
    holder_name="Jane",
    email="j@x.com",
    account_type="SAVINGS",
    balance=10.0,
    status=AccountStatus.ACTIVE,
    created_at="2026-01-01T00:00:00+00:00",
)


class FakeIdempotencyStore:
    def __init__(self, seen: set[str] | None = None) -> None:
        self._seen: set[str] = seen if seen is not None else set()

    def mark_if_first(self, key: str, ttl_seconds: int) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def _deps(seen: set[str] | None = None, account: Account | None = ACC) -> SfnDeps:
    repo = InMemoryAccountRepository()
    if account is not None:
        repo.save(account)
    return SfnDeps(idempotency_store=FakeIdempotencyStore(seen), get=GetAccountUseCase(repo))


def test_procesa_el_paso_y_devuelve_salida() -> None:
    out = process_sfn_task({"accountId": "acc-1", "executionId": "exec-1"}, _deps())
    assert out == {"accountId": "acc-1", "status": "ACTIVE", "processed": True}


def test_idempotente_en_reintento_del_estado() -> None:
    seen: set[str] = set()
    first = process_sfn_task({"accountId": "acc-1", "executionId": "exec-1"}, _deps(seen))
    retry = process_sfn_task({"accountId": "acc-1", "executionId": "exec-1"}, _deps(seen))
    assert first["processed"] is True
    assert retry["processed"] is False


def test_propaga_error_crudo_para_catch_del_estado() -> None:
    with pytest.raises(AccountNotFoundError):
        process_sfn_task({"accountId": "missing", "executionId": "exec-2"}, _deps(account=None))
