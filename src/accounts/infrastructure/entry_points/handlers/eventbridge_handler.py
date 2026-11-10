"""Consumidor EventBridge (bus de eventos) idempotente.

El evento se deduplica por su id (SRV-O-002); reprocesos at-least-once no duplican el
efecto.
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


@dataclass(frozen=True, slots=True)
class EventBridgeDeps:
    idempotency_store: IIdempotencyStore
    process: Callable[[Event], None]


def process_eventbridge(event: Event, deps: EventBridgeDeps) -> None:
    event_id = str(event.get("id", ""))
    is_first = deps.idempotency_store.mark_if_first(f"eb:{event_id}", DEDUPE_TTL_SECONDS)
    if not is_first:
        logger.info("evento EventBridge duplicado; se ignora", extra={"id": event_id})
        return
    deps.process(event)


def _default_process(event: Event) -> None:
    logger.info(
        "procesando evento EventBridge",
        extra={"detailType": event.get("detail-type"), "source": event.get("source")},
    )


def handler(event: Event, _context: object = None) -> None:
    process_eventbridge(
        event,
        EventBridgeDeps(
            idempotency_store=get_container().idempotency_store, process=_default_process
        ),
    )
