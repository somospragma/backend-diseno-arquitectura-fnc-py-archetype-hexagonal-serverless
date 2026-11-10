from __future__ import annotations

import time
from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from accounts.infrastructure.driven_adapters.dynamodb.dynamo_idempotency_store import (
    DynamoIdempotencyStore,
)


@pytest.fixture
def table() -> Iterator[object]:
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="idempotency",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ddb.Table("idempotency")


def test_primera_vez_devuelve_true(table: object) -> None:
    store = DynamoIdempotencyStore(table)
    assert store.mark_if_first("k1", 3600) is True


def test_duplicado_devuelve_false(table: object) -> None:
    store = DynamoIdempotencyStore(table)
    assert store.mark_if_first("k1", 3600) is True
    assert store.mark_if_first("k1", 3600) is False  # ConditionalCheckFailed


def test_guarda_ttl_futuro(table: object) -> None:
    store = DynamoIdempotencyStore(table)
    before = int(time.time())
    store.mark_if_first("k2", 3600)
    item = table.get_item(Key={"id": "k2"})["Item"]  # type: ignore[attr-defined]
    assert int(item["expiresAt"]) > before
