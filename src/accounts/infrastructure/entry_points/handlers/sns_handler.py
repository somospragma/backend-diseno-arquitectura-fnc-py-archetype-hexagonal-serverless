"""Consumidor SNS (fan-out) idempotente.

Cada record se deduplica por su MessageId (SRV-O-002); reprocesos at-least-once no
duplican el efecto.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from accounts.application.composition.container import get_container
from accounts.domain.ports.messaging import IIdempotencyStore
from accounts.infrastructure.helpers.observability import logger

DEDUPE_TTL_SECONDS = 6 * 60 * 60  # 6h

Event = dict[str, Any]
Record = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SnsDeps:
    idempotency_store: IIdempotencyStore
    process: Callable[[Record], None]


def process_sns_event(event: Event, deps: SnsDeps) -> None:
    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        message_id = sns.get("MessageId", "")
        is_first = deps.idempotency_store.mark_if_first(f"sns:{message_id}", DEDUPE_TTL_SECONDS)
        if not is_first:
            logger.info("notificacion SNS duplicada; se ignora", extra={"messageId": message_id})
            continue
        deps.process(record)


def _default_process(record: Record) -> None:
    sns = record.get("Sns", {})
    logger.info("procesando notificacion SNS", extra={"messageId": sns.get("MessageId")})


def handler(event: Event, _context: object = None) -> None:
    process_sns_event(
        event,
        SnsDeps(idempotency_store=get_container().idempotency_store, process=_default_process),
    )
