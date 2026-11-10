"""Publisher de eventos de dominio a un bus EventBridge.

Esquema versionado en el detail; DetailType estable por tipo de evento. Traduce el
fallo tecnico.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from accounts.domain.model.account import AccountEvent
from accounts.domain.model.errors import TechnicalError
from accounts.domain.ports.messaging import IEventPublisher

SCHEMA_VERSION = "1"


class EventBridgePublisher(IEventPublisher):
    def __init__(self, client: Any, bus_name: str, source: str = "pragma.accounts") -> None:
        self._client = client
        self._bus_name = bus_name
        self._source = source

    def publish(self, event: AccountEvent) -> None:
        detail = {"schemaVersion": SCHEMA_VERSION, **asdict(event)}
        try:
            res = self._client.put_events(
                Entries=[
                    {
                        "EventBusName": self._bus_name,
                        "Source": self._source,
                        "DetailType": event.type,
                        "Detail": json.dumps(detail),
                    }
                ]
            )
        except Exception as e:
            raise TechnicalError("ACC-500-004", "EventBridge publish failed", e) from e
        if res.get("FailedEntryCount", 0) > 0:
            raise TechnicalError("ACC-500-004", "EventBridge put failed entries")
