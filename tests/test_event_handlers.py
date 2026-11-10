from __future__ import annotations

from accounts.infrastructure.entry_points.handlers.eventbridge_handler import (
    EventBridgeDeps,
    process_eventbridge,
)
from accounts.infrastructure.entry_points.handlers.sns_handler import SnsDeps, process_sns_event
from accounts.infrastructure.entry_points.handlers.sqs_handler import SqsDeps, process_sqs_batch


class FakeIdempotencyStore:
    """Marca la primera vez True; las claves ya vistas devuelven False."""

    def __init__(self, seen: set[str] | None = None) -> None:
        self._seen: set[str] = seen if seen is not None else set()

    def mark_if_first(self, key: str, ttl_seconds: int) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


# ---- SQS ----


def test_sqs_un_record_veneno_no_tumba_el_batch() -> None:
    processed: list[str] = []

    def process(record: dict) -> None:
        if record["messageId"] == "bad":
            raise RuntimeError("boom")
        processed.append(record["messageId"])

    event = {"Records": [{"messageId": "ok-1"}, {"messageId": "bad"}, {"messageId": "ok-2"}]}
    out = process_sqs_batch(event, SqsDeps(FakeIdempotencyStore(), process))
    assert out == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
    assert processed == ["ok-1", "ok-2"]


def test_sqs_duplicado_se_ignora() -> None:
    calls: list[str] = []
    store = FakeIdempotencyStore(seen={"sqs:dup"})
    event = {"Records": [{"messageId": "dup"}]}
    out = process_sqs_batch(event, SqsDeps(store, lambda r: calls.append(r["messageId"])))
    assert out == {"batchItemFailures": []}
    assert calls == []  # no reproceso


def test_sqs_batch_todo_ok() -> None:
    event = {"Records": [{"messageId": "a"}, {"messageId": "b"}]}
    out = process_sqs_batch(event, SqsDeps(FakeIdempotencyStore(), lambda r: None))
    assert out == {"batchItemFailures": []}


# ---- SNS ----


def test_sns_procesa_y_deduplica() -> None:
    calls: list[str] = []

    def process(record: dict) -> None:
        calls.append(record["Sns"]["MessageId"])

    event = {"Records": [{"Sns": {"MessageId": "m1"}}, {"Sns": {"MessageId": "m1"}}]}
    process_sns_event(event, SnsDeps(FakeIdempotencyStore(), process))
    assert calls == ["m1"]  # el segundo es duplicado


# ---- EventBridge ----


def test_eventbridge_procesa_y_deduplica() -> None:
    calls: list[str] = []

    def process(event: dict) -> None:
        calls.append(str(event["id"]))

    ev = {"id": "e1", "detail-type": "AccountCreated", "source": "pragma.accounts"}
    deps = EventBridgeDeps(FakeIdempotencyStore(), process)
    process_eventbridge(ev, deps)
    process_eventbridge(ev, deps)  # duplicado
    assert calls == ["e1"]
