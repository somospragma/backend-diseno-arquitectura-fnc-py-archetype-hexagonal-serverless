from __future__ import annotations

import pytest

from accounts.domain.model.account import Account, AccountSearchCriteria, AccountStatus
from accounts.domain.model.errors import AccountNotFoundError
from accounts.domain.usecases.account_usecases import (
    MAX_LIMIT,
    CreateAccountInput,
    CreateAccountUseCase,
    DeleteAccountUseCase,
    GetAccountUseCase,
    PatchAccountInput,
    PatchAccountUseCase,
    ReplaceAccountInput,
    SearchAccountsUseCase,
    UpdateAccountUseCase,
)
from tests.fakes import InMemoryAccountRepository


def _seed(repo: InMemoryAccountRepository, account_id: str = "acc-1") -> Account:
    account = Account(
        id=account_id,
        holder_name="Jane",
        email="jane@x.com",
        account_type="SAVINGS",
        balance=10.0,
        status=AccountStatus.ACTIVE,
        created_at="2026-01-01T00:00:00+00:00",
    )
    return repo.save(account)


def test_create_persiste_y_genera_id() -> None:
    repo = InMemoryAccountRepository()
    out = CreateAccountUseCase(repo).execute(
        CreateAccountInput(
            holder_name="Ada", email="ada@x.com", account_type="CHECKING", initial_balance=5.0
        )
    )
    assert out.id
    assert out.status == AccountStatus.ACTIVE
    assert repo.find_by_id(out.id) is not None


def test_get_devuelve_o_falla() -> None:
    repo = InMemoryAccountRepository()
    _seed(repo)
    assert GetAccountUseCase(repo).execute("acc-1").id == "acc-1"
    with pytest.raises(AccountNotFoundError):
        GetAccountUseCase(repo).execute("nope")


def test_update_reemplaza_preservando_id_y_created_at() -> None:
    repo = InMemoryAccountRepository()
    original = _seed(repo)
    out = UpdateAccountUseCase(repo).execute(
        "acc-1",
        ReplaceAccountInput(
            holder_name="New",
            email="new@x.com",
            account_type="CHECKING",
            balance=99.0,
            status=AccountStatus.FROZEN,
        ),
    )
    assert out.id == "acc-1"
    assert out.created_at == original.created_at
    assert out.holder_name == "New"
    assert out.status == AccountStatus.FROZEN


def test_update_inexistente_falla() -> None:
    repo = InMemoryAccountRepository()
    with pytest.raises(AccountNotFoundError):
        UpdateAccountUseCase(repo).execute(
            "x",
            ReplaceAccountInput(
                holder_name="a",
                email="a@x.com",
                account_type="A",
                balance=0.0,
                status=AccountStatus.ACTIVE,
            ),
        )


def test_patch_aplica_solo_campos_presentes() -> None:
    repo = InMemoryAccountRepository()
    _seed(repo)
    out = PatchAccountUseCase(repo).execute("acc-1", PatchAccountInput(balance=42.0))
    assert out.balance == 42.0
    assert out.holder_name == "Jane"  # sin cambios


def test_patch_inexistente_falla() -> None:
    repo = InMemoryAccountRepository()
    with pytest.raises(AccountNotFoundError):
        PatchAccountUseCase(repo).execute("x", PatchAccountInput(email="z@x.com"))


def test_patch_actualiza_todos_los_campos() -> None:
    repo = InMemoryAccountRepository()
    _seed(repo)
    out = PatchAccountUseCase(repo).execute(
        "acc-1",
        PatchAccountInput(
            holder_name="H",
            email="h@x.com",
            account_type="T",
            status=AccountStatus.CLOSED,
            balance=1.0,
        ),
    )
    assert (out.holder_name, out.email, out.account_type, out.status, out.balance) == (
        "H",
        "h@x.com",
        "T",
        AccountStatus.CLOSED,
        1.0,
    )


def test_delete_borra_o_falla() -> None:
    repo = InMemoryAccountRepository()
    _seed(repo)
    DeleteAccountUseCase(repo).execute("acc-1")
    assert repo.find_by_id("acc-1") is None
    with pytest.raises(AccountNotFoundError):
        DeleteAccountUseCase(repo).execute("acc-1")


def test_search_aplica_tope_duro() -> None:
    repo = InMemoryAccountRepository()
    for i in range(5):
        _seed(repo, f"acc-{i}")
    uc = SearchAccountsUseCase(repo)
    assert len(uc.execute(AccountSearchCriteria(status=AccountStatus.ACTIVE), 2)) == 2
    # limit fuera de rango se acota a [1, MAX_LIMIT]
    assert len(uc.execute(AccountSearchCriteria(), 0)) == 1
    assert len(uc.execute(AccountSearchCriteria(), MAX_LIMIT + 500)) == 5
