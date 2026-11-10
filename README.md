# Accounts Serverless (Python)

Arquetipo base de Pragma para microservicios **serverless** en **Python 3.13** con
arquitectura hexagonal, gestionado con **uv** y empaquetado como Lambda. Es el
showcase de referencia de la policy `pragma-python-serverless`: un dominio de ejemplo
(`accounts`) que ejercita todo el framework de madurez backend enfocado en serverless.

Es el equivalente Python del arquetipo `node-serverless`: misma estructura hexagonal,
mismos handlers (API Gateway / SQS / SNS / EventBridge), mismas reglas SRV-*.

No es solo AWS Lambda como concepto aislado: es el patron general serverless (handlers
por evento, sin estado en memoria, idempotencia, cold start, partial batch failure)
sobre AWS (API Gateway, SQS, SNS, EventBridge, DynamoDB).

## Requisitos

- Python 3.13 (uv puede instalarlo: `uv python install 3.13`).
- uv >= 0.7 (gestor de paquetes y entornos de Python).

## Comandos

| Comando | Descripcion |
|---|---|
| `uv sync` | Instala dependencias (lockfile `uv.lock`, versiones resueltas y reproducibles). |
| `uv run mypy src` | Chequeo de tipos estricto. |
| `uv run ruff check .` | Linter. |
| `uv run ruff format --check .` | Verifica formato. |
| `uv run pytest` | pytest + cobertura con gate `--cov-fail-under=90`. |

No hay `build` de bundle como en Node: el artefacto de despliegue es el codigo Python
+ dependencias (empaquetadas por la IaC de despliegue — SAM/CDK/Terraform — o un layer).
El **AWS SDK (boto3) lo provee el runtime de Lambda**, por eso boto3 es dependencia de
desarrollo/tests pero NO se empaqueta (SRV-BP-006, cold start).

## Estructura hexagonal

```
src/accounts/
  domain/                          # NUCLEO framework-free (sin boto3, sin handlers)
    model/                         # account.py (Account, AccountStatus, AccountEvent), errors.py
    ports/                         # IAccountRepository, IIdempotencyStore, IEventPublisher,
                                   # INotificationPublisher, ICacheGateway (typing.Protocol)
    usecases/                      # Create/Get/Update/Patch/Delete/Search (logica de negocio)
  infrastructure/
    entry_points/
      handlers/                    # Handlers serverless (adaptadores de entrada por evento)
        api_gateway_handler.py     #  - API Gateway (REST proxy, todos los verbos + POST /search)
        sqs_handler.py             #  - SQS (partial batch failure + idempotencia)
        sns_handler.py             #  - SNS (fan-out)
        eventbridge_handler.py     #  - EventBridge (bus de eventos)
      http/                        # response.py (Problem Details + headers seguridad), dto.py (Pydantic v2)
    driven_adapters/               # Adaptadores de salida (implementan los ports)
      dynamodb/                    #  - Repositorio (Query, NUNCA Scan) + store de idempotencia
      sns/                         #  - Publisher de notificaciones
      eventbridge/                 #  - Publisher de eventos
      cache/                       #  - Redis (TTL obligatorio + degradacion)
      rds/                         #  - Pool consciente de Lambda (max_size=1, fuera del handler)
    helpers/                       # masking (PII), observability (Powertools logger/metrics/tracer)
  application/
    composition/                   # container.py (composition root; get_container() lazy singleton)
tests/                             # pytest + moto (sin SAM/LocalStack)
```

Regla de dependencia hacia adentro: `domain/` no importa nada de `infrastructure/`,
`application/` ni boto3. Los ports se declaran como `typing.Protocol` (tipado
estructural). Los handlers exportan una funcion core testeable (`route_api_gateway`,
`process_sqs_batch`, `process_sns_event`, `process_eventbridge`) y un `handler` que la
cablea con el `container`.

## Handlers serverless

- **API Gateway** (`api_gateway_handler.py`): REST proxy `/api/v1/accounts`. Ejemplifica
  GET (uno), POST (201), PUT, PATCH, DELETE (204) y busqueda portable `POST /accounts/search`
  (QUERY es aspiracional: API Gateway no enruta el metodo QUERY).
- **SQS** (`sqs_handler.py`): partial batch failure (`batchItemFailures`, SRV-BP-007) e
  idempotencia por `messageId` (SRV-O-002).
- **SNS** (`sns_handler.py`): consumo de notificaciones fan-out, idempotente por `MessageId`.
- **EventBridge** (`eventbridge_handler.py`): consumo de eventos del bus, idempotente por `id`.
- **Step Functions task** (`sfn_task_handler.py`): un paso de orquestacion. Recibe el input del
  estado `Task` (no un evento API GW/SQS), delega en un use case y devuelve la salida para el
  siguiente estado. Idempotente por `executionId`. Los errores se propagan crudos: el `Retry`/`Catch`
  del estado en el ASL decide el reintento, no un try/except en el codigo. La maquina de estados de
  referencia esta en `statemachine/accounts.asl.json` (Retry/Catch por estado, `TimeoutSeconds`,
  `Map` con `MaxConcurrency`, ruta de fallo a DLQ). Aplica solo si el servicio orquesta con SFN.

## Alineacion con el framework serverless (SRV-*)

- **SRV-O-002 Idempotencia**: `IIdempotencyStore` + `DynamoIdempotencyStore` (put condicional
  `attribute_not_exists` con TTL). Handlers SQS/SNS/EventBridge deduplican por id de evento.
- **SRV-O-004 Sin estado en memoria**: el `container` (lazy `@lru_cache`) y los clientes boto3
  se crean una vez por contenedor (warm start) pero NO guardan estado de negocio mutable; el
  estado vive en DynamoDB.
- **SRV-O-005 Conexiones conscientes de Lambda**: `rds/connection_pool.py` crea el pool con
  `max_size=1` FUERA del handler (singleton por contenedor). Alternativas validas: RDS Proxy / Data API.
- **SRV-BP-006 Cold start**: boto3 no se empaqueta (lo provee el runtime); dependencias minimas.
- **SRV-BP-007 Partial batch failure**: el handler SQS retorna `batchItemFailures`.

## Observabilidad y errores

- Logs estructurados JSON, metricas EMF y tracing X-Ray con AWS Lambda Powertools
  (`helpers/observability.py`), sin PII (`helpers/masking.py`).
- Errores tipo RFC 7807 (`http/response.py`): `Problem Details` con headers de seguridad
  (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy) y sin exponer detalle
  interno en 5xx.
- Validacion de entrada estricta con Pydantic v2 (`http/dto.py`, `extra="forbid"`).

## Nota sobre `/actuator`

En serverless NO aplica un endpoint `/actuator/health` estilo Spring: el health y las metricas
se observan via CloudWatch/Powertools. La observabilidad se resuelve con logs/metrics/traces,
no con un endpoint de management embebido.

## Testing

Tests con pytest y `moto` (mock de AWS en memoria, sin SAM ni LocalStack): cada handler expone
una funcion core testeable, los adaptadores DynamoDB/SNS/EventBridge se prueban con `moto`, y
Redis/RDS con fakes inyectados. Gate de cobertura `--cov-fail-under=90` en `pyproject.toml`.
