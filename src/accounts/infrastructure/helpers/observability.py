"""Observabilidad con AWS Lambda Powertools (OBS-*).

Logging estructurado JSON con correlation id, metricas EMF y tracing X-Ray.
Instancias a nivel de modulo (reutilizadas entre invocaciones); NO guardan estado
de negocio, solo config -> compatible con SRV-O-004.
"""

from __future__ import annotations

from aws_lambda_powertools import Logger, Metrics, Tracer

SERVICE_NAME = "accounts-serverless"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace="Pragma/Accounts", service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)
