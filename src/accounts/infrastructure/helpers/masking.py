"""Enmascarado de datos sensibles (PII) para logs y respuestas (DSC-O-003).

El email nunca se expone completo.
"""

from __future__ import annotations

from accounts.domain.model.account import Account


def mask_email(email: str) -> str:
    at = email.find("@")
    if at <= 0:
        return "****"
    return f"****{email[at:]}"


def mask_account(account: Account) -> Account:
    """Devuelve una copia de la cuenta con el email enmascarado."""
    return account.with_changes(email=mask_email(account.email))
