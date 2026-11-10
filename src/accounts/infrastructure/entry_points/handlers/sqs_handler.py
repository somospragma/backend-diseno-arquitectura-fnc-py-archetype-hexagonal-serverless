"""Consumidor SQS con PARTIAL BATCH FAILURE (SRV-BP-007) e IDEMPOTENCIA (SRV-O-002).

- Cada record se procesa aislado: un fallo NO tumba el batch entero.
- Los que fallan se reportan en batchItemFailures para que SQS los reintegre (y a
  DLQ tras maxReceiveCount). Requiere ReportBatchItemFailures en el ESM.
- Dedupe por messageId: reprocesos at-least-once no duplican el efecto.
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
class SqsDeps:
    idempotency_store: IIdempotencyStore
    process: Callable[[Record], None]


def process_sqs_batch(event: Event, deps: SqsDeps) -> dict[str, list[dict[str, str]]]:
    batch_item_failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        message_id = record.get("messageId", "")
        try:
            is_first = deps.idempotency_store.mark_if_first(f"sqs:{message_id}", DEDUPE_TTL_SECONDS)
            if not is_first:
                logger.info("mensaje SQS duplicado; se ignora", extra={"messageId": message_id})
                continue  # ya procesado: exito (no reintentar)
            deps.process(record)
        except Exception as err:
            logger.error(
                "error procesando record SQS; se reintenta (partial batch failure)",
                extra={"messageId": message_id, "error": str(err)},
            )
            batch_item_failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": batch_item_failures}


def _default_process(record: Record) -> None:
    logger.info("procesando mensaje SQS", extra={"messageId": record.get("messageId")})


def handler(event: Event, _context: object = None) -> dict[str, list[dict[str, str]]]:
    return process_sqs_batch(
        event,
        SqsDeps(idempotency_store=get_container().idempotency_store, process=_default_process),
    )
