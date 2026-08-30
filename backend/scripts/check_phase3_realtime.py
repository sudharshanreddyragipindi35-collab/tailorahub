from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tracker_service import TrackerConnectionManager


class ProbeWebSocket:
    def __init__(self) -> None:
        self.messages: asyncio.Queue[dict] = asyncio.Queue()

    async def send_json(self, payload: dict) -> None:
        await self.messages.put(payload)


async def main() -> None:
    redis_url = os.environ.get("PHASE3_REDIS_URL", "redis://127.0.0.1:6380/0")
    first = TrackerConnectionManager(backplane="redis", redis_url=redis_url, channel_prefix="tailorahub:phase3-check")
    second = TrackerConnectionManager(backplane="redis", redis_url=redis_url, channel_prefix="tailorahub:phase3-check")
    probe = ProbeWebSocket()
    second._rooms["booking-check"].add(probe)
    await first.start()
    await second.start()
    try:
        for _ in range(40):
            if first.status["connected"] and second.status["connected"]:
                break
            await asyncio.sleep(0.05)
        if not first.status["connected"] or not second.status["connected"]:
            raise RuntimeError("Redis subscribers did not become ready")
        await first.broadcast("booking-check", {"status": "cross-container-ok"})
        payload = await asyncio.wait_for(probe.messages.get(), timeout=3)
        if payload != {"status": "cross-container-ok"}:
            raise RuntimeError(f"Unexpected event payload: {payload!r}")
        print("Phase 3 Redis cross-instance event check passed")
    finally:
        await first.stop()
        await second.stop()


if __name__ == "__main__":
    asyncio.run(main())
