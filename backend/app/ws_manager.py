import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WsHub:
    """In-memory pub/sub: nurse clients subscribe to a bed key; we fan out JSON
    events. Patient gateways hold one socket per device for inbound commands.

    Also tracks nurse presence (which user_ids currently hold a live bed socket)
    and which devices have a live gateway socket — used for the dashboard's
    "online nurses" and "active/connected" indicators.

    Single-process only — fine for free-tier Render where the app runs as one
    worker. If we ever scale horizontally we'd swap this for Redis pub/sub.
    """

    def __init__(self) -> None:
        self._beds: dict[str, set[WebSocket]] = defaultdict(set)
        self._gateways: dict[str, WebSocket] = {}  # device_id → ws
        self._presence: dict[str, int] = defaultdict(int)  # user_id → open socket count
        self._lock = asyncio.Lock()

    # ----- nurse bed feeds -----

    async def join_bed(self, bed_id: uuid.UUID, ws: WebSocket, user_id: uuid.UUID) -> None:
        async with self._lock:
            self._beds[str(bed_id)].add(ws)
            self._presence[str(user_id)] += 1

    async def leave_bed(self, bed_id: uuid.UUID, ws: WebSocket, user_id: uuid.UUID) -> None:
        async with self._lock:
            self._beds.get(str(bed_id), set()).discard(ws)
            uid = str(user_id)
            if self._presence.get(uid):
                self._presence[uid] -= 1
                if self._presence[uid] <= 0:
                    del self._presence[uid]

    async def broadcast_bed(self, bed_id: uuid.UUID, event: dict[str, Any]) -> None:
        targets = list(self._beds.get(str(bed_id), set()))
        if not targets:
            return
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception as e:  # noqa: BLE001
                logger.info("bed ws dropped: %s", e)
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._beds.get(str(bed_id), set()).discard(ws)

    # ----- presence queries -----

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        return self._presence.get(str(user_id), 0) > 0

    def online_user_ids(self) -> set[str]:
        return {uid for uid, n in self._presence.items() if n > 0}

    # ----- patient gateways -----

    async def connect_gateway(self, device_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            # only one gateway connection per device — drop the old one
            existing = self._gateways.get(str(device_id))
            if existing and existing is not ws:
                try:
                    await existing.close()
                except Exception:  # noqa: BLE001
                    pass
            self._gateways[str(device_id)] = ws

    async def disconnect_gateway(self, device_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            current = self._gateways.get(str(device_id))
            if current is ws:
                del self._gateways[str(device_id)]

    def is_gateway_connected(self, device_id: uuid.UUID) -> bool:
        return str(device_id) in self._gateways

    def connected_device_ids(self) -> set[str]:
        return set(self._gateways.keys())

    async def send_to_gateway(self, device_id: uuid.UUID, event: dict[str, Any]) -> bool:
        ws = self._gateways.get(str(device_id))
        if not ws:
            return False
        try:
            await ws.send_json(event)
            return True
        except Exception as e:  # noqa: BLE001
            logger.info("gateway ws dropped: %s", e)
            async with self._lock:
                if self._gateways.get(str(device_id)) is ws:
                    del self._gateways[str(device_id)]
            return False


hub = WsHub()
