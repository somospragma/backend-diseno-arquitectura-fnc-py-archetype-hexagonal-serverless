"""Publisher de notificaciones fan-out a SNS.

Adjunta el esquema versionado como message attribute (MSG-O-004) y traduce el fallo
tecnico sin propagarlo crudo.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from accounts.domain.model.account import AccountEvent
from accounts.domain.model.errors import TechnicalError
from accounts.domain.ports.messaging import INotificationPublisher

SCHEMA_VERSION = "1"


class SnsNotificationPublisher(INotificationPublisher):
    def __init__(self, sns_client: Any, topic_arn: str) -> None:
        self._sns = sns_client
        self._topic_arn = topic_arn

    def notify(self, event: AccountEvent) -> None:
        message = {"schemaVersion": SCHEMA_VERSION, **asdict(event)}
        try:
            self._sns.publish(
                TopicArn=self._topic_arn,
                Message=json.dumps(message),
                MessageAttributes={
                    "schemaVersion": {"DataType": "String", "StringValue": SCHEMA_VERSION},
                    "eventType": {"DataType": "String", "StringValue": event.type},
                },
            )
        except Exception as e:
            raise TechnicalError("ACC-500-003", "SNS publish failed", e) from e
