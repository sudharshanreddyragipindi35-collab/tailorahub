from __future__ import annotations

import asyncio
import signal

from app.settings import settings
from app.tasks.scheduler import configure_jobs, scheduler
from app.observability import configure_logging


async def main() -> None:
    configure_logging()
    if settings.task_queue_backend != "sqs":
        raise RuntimeError("The production scheduler requires TASK_QUEUE_BACKEND=sqs")
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stopped.set)
        except NotImplementedError:
            pass
    configure_jobs()
    scheduler.start()
    try:
        await stopped.wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
