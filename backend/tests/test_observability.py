from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observability import JsonLogFormatter, emit_metric, reset_request_id, set_request_id


def test_request_id_is_returned_and_valid_client_value_is_preserved():
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"X-Request-ID": "phase8-request-123"})
    client.close()

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase8-request-123"


def test_invalid_request_id_is_replaced():
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"X-Request-ID": "invalid value with spaces"})
    client.close()

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid value with spaces"
    assert len(response.headers["X-Request-ID"]) == 32


def test_json_formatter_includes_request_context_and_safe_fields():
    token = set_request_id("phase8-log-123")
    try:
        record = logging.LogRecord("tailorahub.test", logging.INFO, __file__, 1, "completed", (), None)
        record.event = "http_request_completed"
        record.status_code = 200
        payload = json.loads(JsonLogFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["requestId"] == "phase8-log-123"
    assert payload["event"] == "http_request_completed"
    assert payload["status_code"] == 200
    assert payload["message"] == "completed"


def test_embedded_metric_uses_bounded_environment_dimension(monkeypatch):
    records: list[logging.LogRecord] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    monkeypatch.setenv("CLOUDWATCH_EMF_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    logger = logging.getLogger("tailorahub.metrics")
    handler = CaptureHandler()
    logger.addHandler(handler)
    try:
        emit_metric("PaymentWebhookFailure", 1, Category="invalid_signature")
    finally:
        logger.removeHandler(handler)

    metric = records[-1].msg
    assert metric["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "TailoraHub/Application"
    assert ["Environment"] in metric["_aws"]["CloudWatchMetrics"][0]["Dimensions"]
    assert metric["Environment"] == "test"
    assert metric["PaymentWebhookFailure"] == 1
