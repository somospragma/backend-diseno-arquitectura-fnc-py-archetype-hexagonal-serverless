from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from accounts.domain.model.account import Account, AccountSearchCriteria, AccountStatus
from accounts.domain.model.errors import TechnicalError
from accounts.infrastructure.driven_adapters.dynamodb.account_dynamo_repository import (
    AccountDynamoRepository,
)

ACC = Account(
    id="acc-1",
    holder_name="Jane",
    email="j@x.com",
    account_type="SAVINGS",
    balance=10.0,
    status=AccountStatus.ACTIVE,
    created_at="2026-01-01T00:00:00+00:00",
)


@pytest.fixture
def table() -> Iterator[object]:
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="accounts",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "status-index",
                    "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ddb.Table("accounts")


def test_save_y_find(table: object) -> None:
    repo = AccountDynamoRepository(table)
    assert repo.save(ACC) == ACC
    found = repo.find_by_id("acc-1")
    assert found is not None
    assert found.id == "acc-1"
    assert found.balance == 10.0


def test_find_inexistente_devuelve_none(table: object) -> None:
    assert AccountDynamoRepository(table).find_by_id("nope") is None


def test_exists_y_delete(table: object) -> None:
    repo = AccountDynamoRepository(table)
    repo.save(ACC)
    assert repo.exists_by_id("acc-1") is True
    repo.delete_by_id("acc-1")
    assert repo.exists_by_id("acc-1") is False


def test_search_usa_query_con_gsi_y_filtro(table: object) -> None:
    repo = AccountDynamoRepository(table)
    repo.save(ACC)
    repo.save(ACC.with_changes(id="acc-2", account_type="CHECKING"))
    out = repo.search(
        AccountSearchCriteria(status=AccountStatus.ACTIVE, account_type="SAVINGS"), 10
    )
    assert [a.id for a in out] == ["acc-1"]


def test_search_por_holder_name(table: object) -> None:
    repo = AccountDynamoRepository(table)
    repo.save(ACC)
    out = repo.search(AccountSearchCriteria(holder_name="Jane"), 10)
    assert len(out) == 1


def test_errores_del_sdk_se_traducen_a_technical() -> None:
    # tabla inexistente (sin moto) -> el cliente falla -> TechnicalError
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        repo = AccountDynamoRepository(ddb.Table("no-existe"))
        with pytest.raises(TechnicalError):
            repo.find_by_id("x")
