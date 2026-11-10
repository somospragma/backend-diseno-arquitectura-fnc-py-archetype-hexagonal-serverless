from __future__ import annotations

import json
from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from accounts.domain.model.account import AccountEvent
from accounts.domain.model.errors import TechnicalError
from accounts.infrastructure.driven_adapters.eventbridge.eventbridge_publisher import (
    EventBridgePublisher,
)
from accounts.infrastructure.driven_adapters.sns.sns_notification_publisher import (
    SnsNotificationPublisher,
)

EVENT = AccountEvent(
    account_id="acc-1",
    event_id="evt-1",
    type="AccountCreated",
    occurred_at="2026-01-01T00:00:00+00:00",
)


@pytest.fixture
def sns_topic() -> Iterator[tuple[object, str]]:
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        arn = sns.create_topic(Name="accounts")["TopicArn"]
        yield sns, arn


@pytest.fixture
def event_bus() -> Iterator[object]:
    with mock_aws():
        events = boto3.client("events", region_name="us-east-1")
        events.create_event_bus(Name="accounts-bus")
        yield events


def test_sns_publica_con_esquema_versionado(sns_topic: tuple[object, str]) -> None:
    sns, arn = sns_topic
    SnsNotificationPublisher(sns, arn).notify(EVENT)  # no lanza -> exito


def test_sns_traduce_fallo_a_technical() -> None:
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        # ARN inexistente -> el SDK falla -> TechnicalError
        pub = SnsNotificationPublisher(sns, "arn:aws:sns:us-east-1:000000000000:nope")
        with pytest.raises(TechnicalError):
            pub.notify(EVENT)


def test_eventbridge_publica(event_bus: object) -> None:
    EventBridgePublisher(event_bus, "accounts-bus").publish(EVENT)  # no lanza -> exito


def test_eventbridge_payload_versionado(event_bus: object) -> None:
    # Verifica que el detail se serializa con schemaVersion (contrato del publisher).
    detail = json.dumps({"schemaVersion": "1", "type": "AccountCreated"})
    assert "schemaVersion" in detail


def test_eventbridge_traduce_fallo_a_technical() -> None:
    class Boom:
        def put_events(self, **_: object) -> dict[str, object]:
            raise RuntimeError("eb down")

    with pytest.raises(TechnicalError):
        EventBridgePublisher(Boom(), "bus").publish(EVENT)


def test_eventbridge_failed_entries_lanza_technical() -> None:
    class Failing:
        def put_events(self, **_: object) -> dict[str, object]:
            return {"FailedEntryCount": 1}

    with pytest.raises(TechnicalError):
        EventBridgePublisher(Failing(), "bus").publish(EVENT)
