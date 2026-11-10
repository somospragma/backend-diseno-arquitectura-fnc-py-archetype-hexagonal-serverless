"""Task de Step Functions (adaptador de entrada de ORQUESTACION).

Un paso del workflow: valida/procesa un elemento y devuelve el resultado para el
siguiente estado. A diferencia de API GW/SQS, aqui NO hay envoltura de evento HTTP
ni Records: el estado entrega directamente el JSON definido en el ASL (tras
InputPath/Parameters). El campo task_token solo llega en integraciones
.waitForTaskToken (callback); en Task sincrona no viene.

Idempotente por execution_id (los reintentos declarados con Retry en el ASL no
duplican el efecto). Los errores se propagan CRUDOS a proposito: es el bloque
Catch/Retry del ESTADO (no un try/except en codigo) quien decide el reintento o la
transicion de fallo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from accounts.application.composition.container import UseCases, get_container
from accounts.domain.ports.messaging import IIdempotencyStore
from accounts.domain.usecases.account_usecases import GetAccountUseCase
from accounts.infrastructure.helpers.masking import mask_account
from accounts.infrastructure.helpers.observability import logger

DEDUPE_TTL_SECONDS = 24 * 60 * 60  # 24h (ventana del workflow)

Event = dict[str, Any]


@dataclass(frozen=True, slots=True)
class SfnDeps:
    idempotency_store: IIdempotencyStore
    get: GetAccountUseCase


def process_sfn_task(event: Event, deps: SfnDeps) -> dict[str, Any]:
    """Procesa un estado Task y devuelve la salida para el siguiente estado."""
    account_id = str(event["accountId"])
    execution_id = str(event["executionId"])
    is_first = deps.idempotency_store.mark_if_first(
        f"sfn:{execution_id}:{account_id}", DEDUPE_TTL_SECONDS
    )
    if not is_first:
        logger.info(
            "paso de workflow ya procesado; se omite (idempotencia)",
            extra={"executionId": execution_id, "accountId": account_id},
        )
    account = deps.get.execute(account_id)
    logger.info("task de workflow procesada", extra={"account": mask_account(account).id})
    return {"accountId": account.id, "status": account.status.value, "processed": is_first}


def handler(event: Event, _context: object = None) -> dict[str, Any]:
    container = get_container()
    uc: UseCases = container.use_cases
    return process_sfn_task(
        event, SfnDeps(idempotency_store=container.idempotency_store, get=uc.get)
    )
