"""Puertos de mensajeria e idempotencia (out)."""

from __future__ import annotations

from typing import Protocol

from accounts.domain.model.account import AccountEvent


class INotificationPublisher(Protocol):
    """Publicar notificaciones fan-out (SNS)."""

    def notify(self, event: AccountEvent) -> None: ...


class IEventPublisher(Protocol):
    """Publicar eventos de dominio a un bus (EventBridge)."""

    def publish(self, event: AccountEvent) -> None: ...


class IIdempotencyStore(Protocol):
    """Idempotencia (SRV-O-002).

    mark_if_first devuelve True SOLO la primera vez que se ve la clave; en
    reprocesos (SQS/EventBridge at-least-once) devuelve False para saltar el
    efecto. El TTL acota la ventana de deduplicacion.
    """

    def mark_if_first(self, key: str, ttl_seconds: int) -> bool: ...
