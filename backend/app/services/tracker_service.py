from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class TrackerConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, booking_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[booking_id].add(websocket)

    def disconnect(self, booking_id: str, websocket: WebSocket) -> None:
        self._rooms[booking_id].discard(websocket)
        if not self._rooms[booking_id]:
            self._rooms.pop(booking_id, None)

    async def broadcast(self, booking_id: str, payload: dict) -> None:
        for websocket in list(self._rooms.get(booking_id, ())):
            await websocket.send_json(payload)


tracker_connections = TrackerConnectionManager()
