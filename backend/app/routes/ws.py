import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Bed, BedMembership, Device, Role, User
from app.security import decode_token
from app.ws_manager import hub

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ws"])


@router.websocket("/ws/beds/{bed_id}")
async def bed_ws(websocket: WebSocket, bed_id: uuid.UUID) -> None:
    """Nurse app live feed for a bed. Auth via short-lived JWT in query string."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="missing token")
        return
    try:
        payload = decode_token(token)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="invalid token")
        return
    if payload.get("typ") != "ws":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="wrong token type")
        return
    user_id = uuid.UUID(payload["sub"])

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.id == user_id))
        allowed = bool(user and user.role == Role.admin)
        if not allowed:
            allowed = bool(
                await db.scalar(
                    select(BedMembership.id).where(
                        BedMembership.bed_id == bed_id, BedMembership.user_id == user_id
                    )
                )
            )
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="not a bed member")
        return

    await websocket.accept()
    await hub.join_bed(bed_id, websocket, user_id)
    try:
        while True:
            await websocket.receive_text()  # we ignore inbound; keep-alive only
    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave_bed(bed_id, websocket, user_id)


@router.websocket("/ws/gateway")
async def gateway_ws(websocket: WebSocket) -> None:
    """Patient gateway holds this open to receive MSG/REM/EMERGENCY commands."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="missing token")
        return
    try:
        payload = decode_token(token)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="invalid token")
        return
    if payload.get("typ") != "device":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="not a device token")
        return
    device_id = uuid.UUID(payload["sub"])

    async with SessionLocal() as db:
        device = await db.scalar(select(Device).where(Device.id == device_id))
    if not device:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="unknown device")
        return

    await websocket.accept()
    await hub.connect_gateway(device_id, websocket)
    logger.info("gateway %s connected", device_id)
    try:
        while True:
            # we ignore inbound on this socket; gateway reports events via REST.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect_gateway(device_id, websocket)
        logger.info("gateway %s disconnected", device_id)
