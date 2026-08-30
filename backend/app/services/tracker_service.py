from __future__ import annotations

import asyncio
from collections import defaultdict
import json
import logging
import uuid

from fastapi import WebSocket
from redis.asyncio import Redis

from app.settings import settings


logger = logging.getLogger(__name__)


class TrackerConnectionManager:
    def __init__(
        self,
        *,
        backplane: str | None = None,
        redis_url: str | None = None,
        channel_prefix: str | None = None,
    ) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self.backplane = (backplane or settings.realtime_backplane).lower()
        if self.backplane not in {"local", "redis"}:
            raise RuntimeError("REALTIME_BACKPLANE must be 'local' or 'redis'")
        self.redis_url = redis_url or settings.redis_url
        self.channel_prefix = (channel_prefix or settings.realtime_channel_prefix).rstrip(":")
        self.instance_id = uuid.uuid4().hex
        self._publisher: Redis | None = None
        self._subscriber: Redis | None = None
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None
        self._running = False
        self._connected = False

    @property
    def status(self) -> dict:
        return {
            "mode": self.backplane,
            "connected": self._connected if self.backplane == "redis" else True,
            "instanceId": self.instance_id,
        }

    async def start(self) -> None:
        if self.backplane != "redis" or self._listener_task:
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_forever(), name="booking-realtime-backplane")

    async def stop(self) -> None:
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        await self._close_subscriber()
        if self._publisher:
            await self._publisher.aclose()
            self._publisher = None
        self._connected = False

    async def _close_subscriber(self) -> None:
        if self._pubsub:
            await self._pubsub.aclose()
            self._pubsub = None
        if self._subscriber:
            await self._subscriber.aclose()
            self._subscriber = None

    async def _listen_forever(self) -> None:
        retry_seconds = 1
        while self._running:
            try:
                self._subscriber = Redis.from_url(self.redis_url, decode_responses=True)
                self._pubsub = self._subscriber.pubsub()
                await self._pubsub.psubscribe(f"{self.channel_prefix}:*")
                self._connected = True
                retry_seconds = 1
                async for message in self._pubsub.listen():
                    if not self._running:
                        return
                    if message.get("type") in {"message", "pmessage"}:
                        await self._handle_backplane_message(message.get("data"))
            except asyncio.CancelledError:
                raise
            except Exception:
                self._connected = False
                logger.exception("Booking real-time Redis subscriber disconnected")
                await self._close_subscriber()
                if self._running:
                    await asyncio.sleep(retry_seconds)
                    retry_seconds = min(retry_seconds * 2, 30)

    async def _handle_backplane_message(self, raw_message) -> None:
        try:
            message = json.loads(raw_message)
            if message.get("source") == self.instance_id:
                return
            booking_id = str(message["bookingId"])
            payload = message["payload"]
            if not isinstance(payload, dict):
                return
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            logger.warning("Ignored invalid booking real-time event")
            return
        await self._broadcast_local(booking_id, payload)

    async def connect(self, booking_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[booking_id].add(websocket)

    def disconnect(self, booking_id: str, websocket: WebSocket) -> None:
        self._rooms[booking_id].discard(websocket)
        if not self._rooms[booking_id]:
            self._rooms.pop(booking_id, None)

    async def _broadcast_local(self, booking_id: str, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._rooms.get(booking_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(booking_id, websocket)

    async def broadcast(self, booking_id: str, payload: dict) -> None:
        await self._broadcast_local(booking_id, payload)
        if self.backplane != "redis":
            return
        message = json.dumps(
            {"source": self.instance_id, "bookingId": booking_id, "payload": payload},
            separators=(",", ":"),
        )
        try:
            if self._publisher is None:
                self._publisher = Redis.from_url(self.redis_url, decode_responses=True)
            await self._publisher.publish(f"{self.channel_prefix}:{booking_id}", message)
        except Exception:
            logger.exception("Could not publish booking real-time event to Redis")
            if self._publisher:
                await self._publisher.aclose()
                self._publisher = None


tracker_connections = TrackerConnectionManager()
