"""Adapter DynamoDB del repositorio de cuentas.

REGLA CLAVE (DAT-O-008): acceso SIEMPRE por Query sobre la clave; NUNCA Scan (que
recorreria toda la tabla). La busqueda por criterios usa un GSI por status con
filtro acotado + Limit.

Se usa el recurso boto3 (Table API), que hace el marshalling/unmarshalling de
tipos DynamoDB automaticamente. El tipo del cliente se inyecta (Any) para no
acoplar el adapter a un cliente concreto y facilitar el test con moto.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Attr, ConditionBase, Key

from accounts.domain.model.account import Account, AccountSearchCriteria, AccountStatus
from accounts.domain.model.errors import TechnicalError
from accounts.domain.ports.account_repository import IAccountRepository


def _to_item(account: Account) -> dict[str, Any]:
    return {
        "id": account.id,
        "holderName": account.holder_name,
        "email": account.email,
        "accountType": account.account_type,
        # DynamoDB no acepta float; se guarda como Decimal.
        "balance": Decimal(str(account.balance)),
        "status": account.status.value,
        "createdAt": account.created_at,
    }


def _from_item(item: dict[str, Any]) -> Account:
    return Account(
        id=str(item["id"]),
        holder_name=str(item["holderName"]),
        email=str(item["email"]),
        account_type=str(item["accountType"]),
        balance=float(item["balance"]),
        status=AccountStatus(str(item["status"])),
        created_at=str(item["createdAt"]),
    )


class AccountDynamoRepository(IAccountRepository):
    def __init__(self, table: Any, status_index: str = "status-index") -> None:
        self._table = table
        self._status_index = status_index

    def save(self, account: Account) -> Account:
        try:
            self._table.put_item(Item=_to_item(account))
            return account
        except Exception as e:
            raise TechnicalError("ACC-500-002", "DynamoDB save failed", e) from e

    def find_by_id(self, account_id: str) -> Account | None:
        try:
            res = self._table.get_item(Key={"id": account_id})
        except Exception as e:
            raise TechnicalError("ACC-500-002", "DynamoDB get failed", e) from e
        item = res.get("Item")
        return _from_item(item) if item else None

    def delete_by_id(self, account_id: str) -> None:
        try:
            self._table.delete_item(Key={"id": account_id})
        except Exception as e:
            raise TechnicalError("ACC-500-002", "DynamoDB delete failed", e) from e

    def exists_by_id(self, account_id: str) -> bool:
        return self.find_by_id(account_id) is not None

    def search(self, criteria: AccountSearchCriteria, limit: int) -> list[Account]:
        # Query por particion del GSI (status). Si no hay status, se usa ACTIVE
        # por defecto para NO caer en Scan.
        status = criteria.status or AccountStatus.ACTIVE
        filter_expr: ConditionBase | None = None
        if criteria.account_type:
            filter_expr = Attr("accountType").eq(criteria.account_type)
        if criteria.holder_name:
            hn = Attr("holderName").eq(criteria.holder_name)
            filter_expr = hn if filter_expr is None else filter_expr & hn
        params: dict[str, Any] = {
            "IndexName": self._status_index,
            "KeyConditionExpression": Key("status").eq(status.value),
            "Limit": limit,
        }
        if filter_expr is not None:
            params["FilterExpression"] = filter_expr
        try:
            res = self._table.query(**params)
        except Exception as e:
            raise TechnicalError("ACC-500-002", "DynamoDB query failed", e) from e
        items = res.get("Items", [])
        return [_from_item(i) for i in items][:limit]
