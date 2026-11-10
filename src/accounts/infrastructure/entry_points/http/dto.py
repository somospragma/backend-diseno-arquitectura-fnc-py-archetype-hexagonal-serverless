"""Validacion de entrada estricta con Pydantic v2 (SEG-O-005): tipos, longitudes, formato.

Equivalente a los esquemas zod del arquetipo Node. `extra="forbid"` rechaza campos
desconocidos (deserializacion estricta).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from accounts.domain.model.account import AccountStatus


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateAccountDto(_Strict):
    holder_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    account_type: str = Field(min_length=1, max_length=40)
    initial_balance: float = Field(ge=0)


class PatchAccountDto(_Strict):
    holder_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    account_type: str | None = Field(default=None, min_length=1, max_length=40)
    status: AccountStatus | None = None
    balance: float | None = Field(default=None, ge=0)


class SearchAccountDto(_Strict):
    status: AccountStatus | None = None
    account_type: str | None = Field(default=None, max_length=40)
    holder_name: str | None = Field(default=None, max_length=120)
