from __future__ import annotations

import json

from accounts.application.composition.container import UseCases
from accounts.domain.usecases.account_usecases import (
    CreateAccountUseCase,
    DeleteAccountUseCase,
    GetAccountUseCase,
    PatchAccountUseCase,
    SearchAccountsUseCase,
    UpdateAccountUseCase,
)
from accounts.infrastructure.entry_points.handlers.api_gateway_handler import (
    ApiDeps,
    route_api_gateway,
)
from tests.fakes import InMemoryAccountRepository

BASE = "/api/v1/accounts"


def _deps() -> ApiDeps:
    repo = InMemoryAccountRepository()
    return ApiDeps(
        use_cases=UseCases(
            create=CreateAccountUseCase(repo),
            get=GetAccountUseCase(repo),
            update=UpdateAccountUseCase(repo),
            patch=PatchAccountUseCase(repo),
            delete=DeleteAccountUseCase(repo),
            search=SearchAccountsUseCase(repo),
        )
    )


def _event(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    account_id: str | None = None,
    qs: dict | None = None,
) -> dict:
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"id": account_id} if account_id else None,
        "queryStringParameters": qs,
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def test_post_crea_201_y_enmascara_email() -> None:
    deps = _deps()
    res = route_api_gateway(
        _event(
            "POST",
            BASE,
            body={
                "holder_name": "Ada",
                "email": "ada@x.com",
                "account_type": "CHECKING",
                "initial_balance": 5,
            },
        ),
        deps,
    )
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert body["email"] == "****@x.com"  # PII enmascarada
    assert body["status"] == "ACTIVE"


def test_ciclo_get_put_patch_delete() -> None:
    deps = _deps()
    created = json.loads(
        route_api_gateway(
            _event(
                "POST",
                BASE,
                body={
                    "holder_name": "Ada",
                    "email": "ada@x.com",
                    "account_type": "CHECKING",
                    "initial_balance": 5,
                },
            ),
            deps,
        )["body"]
    )
    aid = created["id"]

    assert (
        route_api_gateway(_event("GET", f"{BASE}/{aid}", account_id=aid), deps)["statusCode"] == 200
    )

    put = route_api_gateway(
        _event(
            "PUT",
            f"{BASE}/{aid}",
            account_id=aid,
            body={
                "holder_name": "Ada2",
                "email": "ada2@x.com",
                "account_type": "SAVINGS",
                "initial_balance": 9,
            },
        ),
        deps,
    )
    assert put["statusCode"] == 200

    patch = route_api_gateway(
        _event("PATCH", f"{BASE}/{aid}", account_id=aid, body={"balance": 100}), deps
    )
    assert json.loads(patch["body"])["balance"] == 100

    delete = route_api_gateway(_event("DELETE", f"{BASE}/{aid}", account_id=aid), deps)
    assert delete["statusCode"] == 204


def test_get_inexistente_404() -> None:
    res = route_api_gateway(_event("GET", f"{BASE}/nope", account_id="nope"), _deps())
    assert res["statusCode"] == 404


def test_validacion_invalida_400() -> None:
    res = route_api_gateway(_event("POST", BASE, body={"holder_name": ""}), _deps())
    assert res["statusCode"] == 400
    assert json.loads(res["body"])["code"] == "ACC-400-001"


def test_post_search_devuelve_lista_enmascarada() -> None:
    deps = _deps()
    route_api_gateway(
        _event(
            "POST",
            BASE,
            body={
                "holder_name": "Ada",
                "email": "ada@x.com",
                "account_type": "CHECKING",
                "initial_balance": 5,
            },
        ),
        deps,
    )
    res = route_api_gateway(
        _event("POST", f"{BASE}/search", body={"status": "ACTIVE"}, qs={"size": "10"}), deps
    )
    assert res["statusCode"] == 200
    items = json.loads(res["body"])
    assert len(items) == 1
    assert items[0]["email"].startswith("****@")


def test_ruta_desconocida_404() -> None:
    res = route_api_gateway(_event("GET", "/otra/cosa"), _deps())
    assert res["statusCode"] == 404
