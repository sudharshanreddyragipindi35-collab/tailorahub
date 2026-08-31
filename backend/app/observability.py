from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import datetime, timezone
import json
import logging
import os
from typing import Any


_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_STANDARD_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__)
_SAFE_EXTRA_FIELDS = {
    "event",
    "http_method",
    "route",
    "status_code",
    "duration_ms",
    "provider",
    "operation",
    "category",
    "attempt",
    "retry",
    "job_type",
    "job_id",
    "attempts",
    "db_operation",
    "elapsed_ms",
}


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get()


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per line without request bodies, headers, or query strings."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "serviceRole": os.getenv("SERVICE_ROLE", "web"),
            "environment": os.getenv("APP_ENV", "development"),
            "requestId": current_request_id(),
        }
        if isinstance(record.msg, dict) and "_aws" in record.msg:
            payload.update(record.msg)
        else:
            payload["message"] = record.getMessage()
            for field in _SAFE_EXTRA_FIELDS:
                if field not in _STANDARD_LOG_RECORD_FIELDS and hasattr(record, field):
                    payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exceptionType"] = record.exc_info[0].__name__
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    formatter = JsonLogFormatter()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(formatter)


def emit_metric(
    metric_name: str,
    value: float = 1,
    *,
    unit: str = "Count",
    **dimensions: str,
) -> None:
    if os.getenv("CLOUDWATCH_EMF_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        return
    environment = os.getenv("APP_ENV", "development")
    service_role = os.getenv("SERVICE_ROLE", "web")
    safe_dimensions = {
        key: str(value)[:100]
        for key, value in dimensions.items()
        if key and value is not None
    }
    dimension_sets = [["Environment"], ["Environment", "ServiceRole"]]
    if safe_dimensions:
        dimension_sets.append(["Environment", "ServiceRole", *sorted(safe_dimensions)])
    payload: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "TailoraHub/Application",
                    "Dimensions": dimension_sets,
                    "Metrics": [{"Name": metric_name, "Unit": unit}],
                }
            ],
        },
        "Environment": environment,
        "ServiceRole": service_role,
        metric_name: value,
        **safe_dimensions,
    }
    logging.getLogger("tailorahub.metrics").info(payload)
