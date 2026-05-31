import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user
from app.fcm import fan_out
from app.models import Alert, AlertType, BedMembership, Device, Message, Role, User
from app.schemas import AlertOut, MessageIn, MessageOut
from app.ws_manager import hub

router = APIRouter(tags=["messages"])


async def _ensure_member(db: AsyncSession, device_id: uuid.UUID, user: User) -> Device:
    device = await db.scalar(select(Device).where(Device.id == device_id))
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    if user.role == Role.admin:
        return device
    is_member = await db.scalar(
        select(BedMembership.id).where(
            BedMembership.bed_id == device.bed_id, BedMembership.user_id == user.id
        )
    )
    if not is_member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this bed")
    return device


@router.post("/devices/{device_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    device_id: uuid.UUID,
    payload: MessageIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Message:
    device = await _ensure_member(db, device_id, user)
    msg = Message(device_id=device.id, sender_id=user.id, text=payload.text)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    delivered = await hub.send_to_gateway(
        device.id,
        {"kind": "MSG", "message_id": str(msg.id), "text": payload.text},
    )
    if delivered:
        msg.delivered_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
    return msg


@router.get("/devices/{device_id}/messages", response_model=list[MessageOut])
async def list_messages(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[Message]:
    await _ensure_member(db, device_id, user)
    rows = await db.scalars(
        select(Message)
        .where(Message.device_id == device_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(rows)


@router.post("/devices/{device_id}/emergency", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def trigger_emergency(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Alert:
    device = await _ensure_member(db, device_id, user)
    alert = Alert(device_id=device.id, bed_id=device.bed_id, type=AlertType.EMERGENCY)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    nurse_ids = list(
        await db.scalars(
            select(BedMembership.user_id).where(BedMembership.bed_id == device.bed_id)
        )
    )
    await fan_out(
        db,
        nurse_ids,
        title="🚨 EMERGENCY",
        body=device.name or device.serial_id,
        data={
            "kind": "alert.new",
            "alert_id": str(alert.id),
            "bed_id": str(device.bed_id),
            "device_id": str(device.id),
            "type": AlertType.EMERGENCY.value,
            "emergency": "1",
        },
        high_priority=True,
    )
    await hub.broadcast_bed(
        device.bed_id,
        {
            "event": "alert.new",
            "alert_id": str(alert.id),
            "device_id": str(device.id),
            "bed_id": str(device.bed_id),
            "type": AlertType.EMERGENCY.value,
            "created_at": alert.created_at.isoformat(),
        },
    )
    await hub.send_to_gateway(device.id, {"kind": "EMERGENCY"})
    return alert
