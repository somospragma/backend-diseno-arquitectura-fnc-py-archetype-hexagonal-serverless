from __future__ import annotations

import json

from accounts.domain.model.errors import (
    AccountNotFoundError,
    BusinessError,
    DomainError,
    TechnicalError,
)
from accounts.infrastructure.entry_points.http.response import (
    no_content,
    ok,
    problem,
    to_problem,
)


def test_ok_incluye_headers_de_seguridad() -> None:
    res = ok({"a": 1})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "max-age=31536000" in headers["Strict-Transport-Security"]
    assert headers["Content-Security-Policy"] == "default-src 'self'"
    assert json.loads(res["body"]) == {"a": 1}


def test_ok_status_custom() -> None:
    assert ok({}, 201)["statusCode"] == 201


def test_no_content() -> None:
    res = no_content()
    assert res["statusCode"] == 204
    assert res["body"] == ""


def test_problem_content_type() -> None:
    res = problem(422, "ACC-422-001", "invalid", field="email")
    assert res["headers"]["Content-Type"] == "application/problem+json"
    assert json.loads(res["body"]) == {
        "code": "ACC-422-001",
        "status": 422,
        "detail": "invalid",
        "field": "email",
    }


def test_to_problem_business_404() -> None:
    assert to_problem(AccountNotFoundError("x"))["statusCode"] == 404


def test_to_problem_business_generico_422() -> None:
    assert to_problem(BusinessError("ACC-422-002", "nope"))["statusCode"] == 422


def test_to_problem_technical_500_sin_detalle() -> None:
    res = to_problem(TechnicalError("ACC-500-009", "secreto interno"))
    assert res["statusCode"] == 500
    assert json.loads(res["body"])["detail"] == "Internal error"


def test_to_problem_domain_400() -> None:
    class ValidationDomainError(DomainError):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.code = "ACC-400-050"

    res = to_problem(ValidationDomainError("bad"))
    assert res["statusCode"] == 400
    assert json.loads(res["body"])["code"] == "ACC-400-050"


def test_to_problem_desconocido_500() -> None:
    res = to_problem(RuntimeError("boom"))
    assert res["statusCode"] == 500
    assert json.loads(res["body"])["code"] == "ACC-500-001"
