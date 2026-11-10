"""Handler API Gateway (REST proxy integration).

Router HTTP puro (testeable) que ejemplifica los metodos: GET (uno), POST (201),
PUT (reemplazo total), PATCH (parcial), DELETE (204) y una busqueda segura. QUERY es
aspiracional en el stack (API Gateway no enruta QUERY), por eso la busqueda con body
se expone en POST /accounts/search de forma portable.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from accounts.application.composition.container import UseCases, get_container
from accounts.domain.model.account import AccountSearchCriteria, AccountStatus
from accounts.domain.model.errors import BusinessError, DomainError, TechnicalError
from accounts.domain.usecases.account_usecases import (
    CreateAccountInput,
    PatchAccountInput,
    ReplaceAccountInput,
)
from accounts.infrastructure.entry_points.http.dto import (
    CreateAccountDto,
    PatchAccountDto,
    SearchAccountDto,
)
from accounts.infrastructure.entry_points.http.response import (
    ApiResponse,
    no_content,
    ok,
    problem,
    to_problem,
)
from accounts.infrastructure.helpers.masking import mask_account

BASE = "/api/v1/accounts"

# Alias para el dataclass Account -> dict serializable con email enmascarado.
Event = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ApiDeps:
    use_cases: UseCases


def _parse_body(event: Event) -> Any:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body)


def _account_to_json(account: Any) -> dict[str, Any]:
    """Serializa el Account (dataclass) enmascarando la PII."""
    masked = mask_account(account)
    return {
        "id": masked.id,
        "holderName": masked.holder_name,
        "email": masked.email,
        "accountType": masked.account_type,
        "balance": masked.balance,
        "status": masked.status.value,
        "createdAt": masked.created_at,
    }


def route_api_gateway(event: Event, deps: ApiDeps) -> ApiResponse:  # noqa: PLR0911 - un return por verbo HTTP
    method = str(event.get("httpMethod", "")).upper()
    path = str(event.get("path", ""))
    account_id = (event.get("pathParameters") or {}).get("id")
    uc = deps.use_cases
    try:
        if method == "POST" and path == f"{BASE}/search":
            search_dto = SearchAccountDto.model_validate(_parse_body(event))
            size = int((event.get("queryStringParameters") or {}).get("size", 20))
            criteria = AccountSearchCriteria(
                status=search_dto.status,
                account_type=search_dto.account_type,
                holder_name=search_dto.holder_name,
            )
            result = uc.search.execute(criteria, size)
            return ok([_account_to_json(a) for a in result])
        if method == "GET" and account_id:
            return ok(_account_to_json(uc.get.execute(account_id)))
        if method == "POST" and path == BASE:
            create_dto = CreateAccountDto.model_validate(_parse_body(event))
            created = uc.create.execute(
                CreateAccountInput(
                    holder_name=create_dto.holder_name,
                    email=create_dto.email,
                    account_type=create_dto.account_type,
                    initial_balance=create_dto.initial_balance,
                )
            )
            return ok(_account_to_json(created), 201)
        if method == "PUT" and account_id:
            put_dto = CreateAccountDto.model_validate(_parse_body(event))
            updated = uc.update.execute(
                account_id,
                ReplaceAccountInput(
                    holder_name=put_dto.holder_name,
                    email=put_dto.email,
                    account_type=put_dto.account_type,
                    balance=put_dto.initial_balance,
                    status=AccountStatus.ACTIVE,
                ),
            )
            return ok(_account_to_json(updated))
        if method == "PATCH" and account_id:
            patch_dto = PatchAccountDto.model_validate(_parse_body(event))
            patched = uc.patch.execute(
                account_id,
                PatchAccountInput(
                    holder_name=patch_dto.holder_name,
                    email=patch_dto.email,
                    account_type=patch_dto.account_type,
                    status=patch_dto.status,
                    balance=patch_dto.balance,
                ),
            )
            return ok(_account_to_json(patched))
        if method == "DELETE" and account_id:
            uc.delete.execute(account_id)
            return no_content()
        return problem(404, "ACC-404-000", f"No route for {method} {path}")
    except ValidationError:
        return problem(400, "ACC-400-001", "Validation failed")
    except (BusinessError, TechnicalError, DomainError) as err:
        return to_problem(err)


def handler(event: Event, _context: object = None) -> ApiResponse:
    return route_api_gateway(event, ApiDeps(use_cases=get_container().use_cases))
