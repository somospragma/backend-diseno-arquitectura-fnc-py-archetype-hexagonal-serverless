"""Jerarquia de errores de dominio.

Los handlers los traducen a estados HTTP / respuestas (RFC 7807-like). El dominio
nunca conoce codigos HTTP.
"""

from __future__ import annotations


class DomainError(Exception):
    """Error base de dominio. Cada subtipo aporta un codigo estable."""

    code: str = "ACC-500-000"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BusinessError(DomainError):
    """Error de negocio (mapeable a 4xx)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TechnicalError(DomainError):
    """Error tecnico (mapeable a 5xx); nunca expone detalle interno al cliente."""

    def __init__(self, code: str, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.cause = cause


class AccountNotFoundError(BusinessError):
    def __init__(self, account_id: str) -> None:
        super().__init__("ACC-404-001", f"Account not found: {account_id}")
