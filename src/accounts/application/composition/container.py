"""Composition root (wiring).

Se construye UNA vez a nivel de modulo (lazy) y se reutiliza entre invocaciones
calientes; NO guarda estado de negocio mutable (SRV-O-004), solo clientes AWS y use
cases stateless. Los clientes AWS fuera del handler reutilizan conexiones (mejor
cold path).

Se expone `get_container()` con inicializacion diferida para que el import del modulo
NO cree clientes AWS (importante para los tests y para el cold start controlado).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3

from accounts.domain.usecases.account_usecases import (
    CreateAccountUseCase,
    DeleteAccountUseCase,
    GetAccountUseCase,
    PatchAccountUseCase,
    SearchAccountsUseCase,
    UpdateAccountUseCase,
)
from accounts.infrastructure.driven_adapters.dynamodb.account_dynamo_repository import (
    AccountDynamoRepository,
)
from accounts.infrastructure.driven_adapters.dynamodb.dynamo_idempotency_store import (
    DynamoIdempotencyStore,
)
from accounts.infrastructure.driven_adapters.eventbridge.eventbridge_publisher import (
    EventBridgePublisher,
)
from accounts.infrastructure.driven_adapters.sns.sns_notification_publisher import (
    SnsNotificationPublisher,
)


@dataclass(frozen=True, slots=True)
class UseCases:
    create: CreateAccountUseCase
    get: GetAccountUseCase
    update: UpdateAccountUseCase
    patch: PatchAccountUseCase
    delete: DeleteAccountUseCase
    search: SearchAccountsUseCase


@dataclass(frozen=True, slots=True)
class Container:
    repository: AccountDynamoRepository
    idempotency_store: DynamoIdempotencyStore
    notification_publisher: SnsNotificationPublisher
    event_publisher: EventBridgePublisher
    use_cases: UseCases


@lru_cache(maxsize=1)
def get_container() -> Container:
    dynamo = boto3.resource("dynamodb")
    sns = boto3.client("sns")
    events = boto3.client("events")

    accounts_table = dynamo.Table(os.environ.get("ACCOUNTS_TABLE", "accounts"))
    idempotency_table = dynamo.Table(os.environ.get("IDEMPOTENCY_TABLE", "idempotency"))

    repository = AccountDynamoRepository(accounts_table)
    idempotency_store = DynamoIdempotencyStore(idempotency_table)
    notification_publisher = SnsNotificationPublisher(
        sns, os.environ.get("ACCOUNTS_TOPIC_ARN", "arn:topic")
    )
    event_publisher = EventBridgePublisher(events, os.environ.get("EVENT_BUS", "default"))

    return Container(
        repository=repository,
        idempotency_store=idempotency_store,
        notification_publisher=notification_publisher,
        event_publisher=event_publisher,
        use_cases=UseCases(
            create=CreateAccountUseCase(repository),
            get=GetAccountUseCase(repository),
            update=UpdateAccountUseCase(repository),
            patch=PatchAccountUseCase(repository),
            delete=DeleteAccountUseCase(repository),
            search=SearchAccountsUseCase(repository),
        ),
    )
