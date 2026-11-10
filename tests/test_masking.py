from __future__ import annotations

from accounts.domain.model.account import Account, AccountStatus
from accounts.infrastructure.helpers.masking import mask_account, mask_email


def test_mask_email_conserva_dominio() -> None:
    assert mask_email("jane.doe@pragma.com") == "****@pragma.com"


def test_mask_email_sin_arroba_valida() -> None:
    assert mask_email("sin-arroba") == "****"
    assert mask_email("@nolocal.com") == "****"


def test_mask_account_enmascara_email() -> None:
    acc = Account(
        id="acc-1",
        holder_name="Jane",
        email="a@b.com",
        account_type="SAVINGS",
        balance=1.0,
        status=AccountStatus.ACTIVE,
        created_at="2026-01-01T00:00:00+00:00",
    )
    masked = mask_account(acc)
    assert masked.email == "****@b.com"
    assert masked.id == "acc-1"
