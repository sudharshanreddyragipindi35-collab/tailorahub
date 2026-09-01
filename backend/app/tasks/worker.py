from __future__ import annotations

import asyncio
import base64
import csv
from io import StringIO
import json
import logging
import signal
import time

from sqlalchemy import text

from app.db import engine
from app.settings import settings
from app.observability import configure_logging, emit_metric, reset_request_id, set_request_id


logger = logging.getLogger(__name__)
_running = True


def _handle_email(payload: dict) -> dict:
    from app.integrations import email_service

    attachments = []
    for attachment in payload.get("attachments") or []:
        try:
            data = base64.b64decode(attachment.get("data") or "", validate=True)
        except Exception as exc:
            raise ValueError("Invalid email attachment encoding") from exc
        attachments.append({
            "filename": attachment.get("filename") or "attachment",
            "maintype": attachment.get("maintype") or "application",
            "subtype": attachment.get("subtype") or "octet-stream",
            "data": data,
        })
    result = email_service().send(payload["to"], payload["subject"], payload["body"], payload.get("purpose", "default"), attachments=attachments)
    if not result.get("ok"):
        return {**result, "terminalFailure": True, "reason": result.get("reason") or "email_delivery_failed"}
    return result


def _handle_sms_otp(payload: dict) -> dict:
    from app.integrations import sms_service_now

    result = sms_service_now().send_otp(payload["phone"], payload["code"])
    if not result.get("ok"):
        return {**result, "terminalFailure": True, "reason": result.get("reason") or "sms_delivery_failed"}
    return result


def _handle_scheduled(payload: dict) -> dict:
    from app.tasks.scheduler import SCHEDULED_HANDLERS

    handler = SCHEDULED_HANDLERS[payload["name"]]
    asyncio.run(handler())
    return {"ok": True, "scheduledJob": payload["name"]}


def _handle_admin_wallet_export(payload: dict) -> dict:
    from app.services.media_storage import get_media_storage

    clauses = []
    params = {}
    if payload.get("dateFrom"):
        clauses.append("created_at::date >= :date_from")
        params["date_from"] = payload["dateFrom"]
    if payload.get("dateTo"):
        clauses.append("created_at::date <= :date_to")
        params["date_to"] = payload["dateTo"]
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id,type,amount,source_booking_id,created_at FROM admin_wallet_transactions" + where + " ORDER BY created_at DESC LIMIT 100000"),
            params,
        ).mappings().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "amount", "source_booking_id", "created_at"])
    for row in rows:
        writer.writerow([row["id"], row["type"], row["amount"], row["source_booking_id"], row["created_at"]])
    reference = get_media_storage().store_private_bytes(
        f"private/reports/{payload['_jobId']}.csv",
        output.getvalue().encode("utf-8"),
        "text/csv",
    )
    return {"ok": True, "downloadReference": reference, "rowCount": len(rows)}


def _handle_media_postprocess(payload: dict) -> dict:
    from app.services.media_storage import get_media_storage

    return get_media_storage().mark_processed(payload["objectKey"], payload["contentType"])


HANDLERS = {
    "email_delivery": _handle_email,
    "sms_otp_delivery": _handle_sms_otp,
    "scheduled_job": _handle_scheduled,
    "admin_wallet_export": _handle_admin_wallet_export,
    "media_postprocess": _handle_media_postprocess,
}


def execute_task_inline(message: dict) -> dict:
    handler = HANDLERS.get(message.get("jobType"))
    if not handler:
        raise RuntimeError(f"Unsupported background job type: {message.get('jobType')}")
    payload = {**(message.get("payload") or {}), "_jobId": message.get("jobId")}
    return handler(payload)


def _claim(message: dict) -> bool:
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT status,updated_at FROM background_job_receipts WHERE idempotency_key=:key FOR UPDATE"),
            {"key": message["idempotencyKey"]},
        ).mappings().first()
        if row and row["status"] == "completed":
            return False
        connection.execute(
            text(
                """
                INSERT INTO background_job_receipts (idempotency_key,job_id,job_type,status,attempts)
                VALUES (:key,:job_id,:job_type,'processing',1)
                ON CONFLICT (idempotency_key) DO UPDATE SET
                  status='processing', attempts=background_job_receipts.attempts+1,
                  last_error=NULL, updated_at=now()
                """
            ),
            {"key": message["idempotencyKey"], "job_id": message["jobId"], "job_type": message["jobType"]},
        )
    return True


def _finish(message: dict, result: dict) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE background_job_receipts SET status='completed',result=CAST(:result AS jsonb),completed_at=now(),updated_at=now() WHERE idempotency_key=:key"),
            {"key": message["idempotencyKey"], "result": json.dumps(result)},
        )


def _fail(message: dict, error: Exception) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE background_job_receipts SET status='failed',last_error=:error,updated_at=now() WHERE idempotency_key=:key"),
            {"key": message["idempotencyKey"], "error": str(error)[:1000]},
        )


def process_message(message: dict) -> bool:
    token = set_request_id(str(message.get("jobId") or "background-job")[:128])
    try:
        if not _claim(message):
            return True
        try:
            result = execute_task_inline(message)
            _finish(message, result)
            return True
        except Exception as exc:
            _fail(message, exc)
            logger.exception(
                "background_job_failed",
                extra={
                    "event": "background_job_failed",
                    "job_type": str(message.get("jobType") or "unknown"),
                    "job_id": str(message.get("jobId") or "unknown"),
                },
            )
            emit_metric("BackgroundJobFailure", 1, JobType=str(message.get("jobType") or "unknown"))
            raise
    finally:
        reset_request_id(token)


def main() -> None:
    configure_logging()
    if settings.task_queue_backend != "sqs" or not settings.sqs_task_queue_url:
        raise RuntimeError("The worker requires TASK_QUEUE_BACKEND=sqs and SQS_TASK_QUEUE_URL")
    import boto3

    client = boto3.client("sqs", region_name=settings.sqs_region, endpoint_url=settings.sqs_endpoint_url or None)
    signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__("_running", False))
    while _running:
        response = client.receive_message(
            QueueUrl=settings.sqs_task_queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=min(settings.task_long_poll_seconds, 20),
            VisibilityTimeout=settings.task_visibility_timeout_seconds,
            AttributeNames=["ApproximateReceiveCount"],
        )
        for sqs_message in response.get("Messages", []):
            message: dict = {}
            try:
                message = json.loads(sqs_message["Body"])
                process_message(message)
                client.delete_message(QueueUrl=settings.sqs_task_queue_url, ReceiptHandle=sqs_message["ReceiptHandle"])
            except Exception:
                attempts = int(sqs_message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
                delay = min(settings.task_visibility_timeout_seconds * (2 ** max(attempts - 1, 0)), 900)
                client.change_message_visibility(
                    QueueUrl=settings.sqs_task_queue_url,
                    ReceiptHandle=sqs_message["ReceiptHandle"],
                    VisibilityTimeout=delay,
                )
                if not message:
                    logger.exception("background_message_invalid attempts=%s", attempts)
                    emit_metric("BackgroundJobFailure", 1, JobType="invalid_message")
        if not response.get("Messages") and settings.task_long_poll_seconds == 0:
            time.sleep(1)


if __name__ == "__main__":
    main()
