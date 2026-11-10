"""Store de idempotencia sobre DynamoDB (SRV-O-002).

mark_if_first hace un PutItem condicional (attribute_not_exists) con TTL: la primera
vez inserta y devuelve True; en reprocesos la condicion falla y devuelve False para
saltar el efecto. Es el equivalente serverless del SETNX de Redis, sin dependencia
de Redis.
"""

from __future__ import annotations

import time
from typing import Any

from botocore.exceptions import ClientError

from accounts.domain.ports.messaging import IIdempotencyStore


class DynamoIdempotencyStore(IIdempotencyStore):
    def __init__(self, table: Any) -> None:
        self._table = table

    def mark_if_first(self, key: str, ttl_seconds: int) -> bool:
        expires_at = int(time.time()) + ttl_seconds
        try:
            self._table.put_item(
                Item={"id": key, "expiresAt": expires_at},
                ConditionExpression="attribute_not_exists(id)",
            )
            return True
        except ClientError as e:
            # ConditionalCheckFailedException => clave ya vista (duplicado)
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
