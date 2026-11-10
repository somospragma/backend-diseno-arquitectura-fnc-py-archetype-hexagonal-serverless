"""Respuestas HTTP para API Gateway (proxy integration).

Problem Details (RFC 7807-like) y headers de seguridad en todas las respuestas
(API-O-006 / SEG). Nunca expone stack traces ni detalle interno.
"""

from __future__ import annotations

import json
from typing import Any

from accounts.domain.model.errors import BusinessError, DomainError, TechnicalError

# Headers de seguridad en todas las respuestas HTML/JSON (API-O-006 / SEG).
SECURITY_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}

# Alias de tipo para el shape del resultado proxy de API Gateway.
ApiResponse = dict[str, Any]


def ok(body: Any, status: int = 200) -> ApiResponse:
    return {"statusCode": status, "headers": dict(SECURITY_HEADERS), "body": json.dumps(body)}


def no_content() -> ApiResponse:
    return {"statusCode": 204, "headers": dict(SECURITY_HEADERS), "body": ""}


def problem(status: int, code: str, detail: str, **extra: Any) -> ApiResponse:
    """Problem Details (RFC 7807-like). Nunca expone stack traces ni detalle interno."""
    headers = dict(SECURITY_HEADERS)
    headers["Content-Type"] = "application/problem+json"
    payload: dict[str, Any] = {"code": code, "status": status, "detail": detail, **extra}
    return {"statusCode": status, "headers": headers, "body": json.dumps(payload)}


def to_problem(err: Exception) -> ApiResponse:
    """Traduce excepciones de dominio a Problem Details con el estado HTTP correcto."""
    if isinstance(err, BusinessError):
        status = 404 if "404" in err.code else 422
        return problem(status, err.code, err.message)
    if isinstance(err, TechnicalError):
        return problem(500, err.code, "Internal error")  # sin detalle interno
    if isinstance(err, DomainError):
        return problem(400, err.code, err.message)
    return problem(500, "ACC-500-001", "Internal error")
