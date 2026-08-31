from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import uuid

from app.settings import settings


logger = logging.getLogger(__name__)


class TaskQueueError(RuntimeError):
    pass


@dataclass(frozen=True)
class QueuedTask:
    job_id: str
    job_type: str
    idempotency_key: str
    payload: dict

    def as_message(self) -> dict:
        return {
            "version": 1,
            "jobId": self.job_id,
            "jobType": self.job_type,
            "idempotencyKey": self.idempotency_key,
            "payload": self.payload,
        }


class TaskQueue:
    def __init__(self) -> None:
        self.backend = settings.task_queue_backend
        if self.backend not in {"inline", "sqs"}:
            raise TaskQueueError("TASK_QUEUE_BACKEND must be 'inline' or 'sqs'")
        self._client = None

    def _sqs(self):
        if self._client is None:
            import boto3

            self._client = boto3.client("sqs", region_name=settings.sqs_region, endpoint_url=settings.sqs_endpoint_url or None)
        return self._client

    def enqueue(self, job_type: str, payload: dict, idempotency_key: str, delay_seconds: int = 0) -> dict:
        task = QueuedTask(uuid.uuid4().hex, job_type, idempotency_key, payload)
        if self.backend == "inline":
            from app.tasks.worker import execute_task_inline

            result = execute_task_inline(task.as_message())
            return {"queued": False, "mode": "inline", "jobId": task.job_id, "result": result}
        if not settings.sqs_task_queue_url:
            raise TaskQueueError("SQS_TASK_QUEUE_URL is required when TASK_QUEUE_BACKEND=sqs")
        response = self._sqs().send_message(
            QueueUrl=settings.sqs_task_queue_url,
            MessageBody=json.dumps(task.as_message(), separators=(",", ":")),
            DelaySeconds=max(0, min(int(delay_seconds), 900)),
            MessageAttributes={
                "jobType": {"DataType": "String", "StringValue": job_type},
                "idempotencyKey": {"DataType": "String", "StringValue": idempotency_key},
            },
        )
        logger.info("queued_background_job type=%s job_id=%s", job_type, task.job_id)
        return {"queued": True, "mode": "sqs", "jobId": task.job_id, "messageId": response.get("MessageId")}


task_queue = TaskQueue()


def enqueue_task(job_type: str, payload: dict, idempotency_key: str, delay_seconds: int = 0) -> dict:
    return task_queue.enqueue(job_type, payload, idempotency_key, delay_seconds)
