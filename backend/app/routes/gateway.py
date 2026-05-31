import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_device
from app.fcm import fan_out
from app.models import Alert, AlertType, Bed, BedMembership, Device, Room
from app.schemas import AlertOut, GatewayEventIn
from app.ws_manager import hub

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gateway", tags=["gateway"])


_TITLES = {
    AlertType.WATER: "Patient needs water",
    AlertType.MEDICINE: "Patient needs medicine",
    AlertType.HELP: "Patient needs help",
    AlertType.BATHROOM: "Patient needs the bathroom",
    AlertType.EMERGENCY: "🚨 EMERGENCY",
}


@router.post("/events", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def report_event(
    payload: GatewayEventIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(current_device),
) -> Alert:
    bed = await db.scalar(select(Bed).where(Bed.id == device.bed_id))
    room_name = await db.scalar(select(Room.name).where(Room.id == bed.room_id)) if bed else None
    location = " · ".join(p for p in [room_name, bed.label if bed else None] if p) or (
        device.name or device.serial_id
    )

    alert = Alert(device_id=device.id, bed_id=device.bed_id, type=payload.type)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    nurse_ids = list(
        await db.scalars(
            select(BedMembership.user_id).where(BedMembership.bed_id == device.bed_id)
        )
    )

    sent = await fan_out(
        db,
        nurse_ids,
        title=_TITLES.get(payload.type, payload.type.value),
        body=location,
        data={
            "kind": "alert.new",
            "alert_id": str(alert.id),
            "bed_id": str(device.bed_id),
            "device_id": str(device.id),
            "type": payload.type.value,
        },
        high_priority=payload.type == AlertType.EMERGENCY,
    )
    await hub.broadcast_bed(
        device.bed_id,
        {
            "event": "alert.new",
            "alert_id": str(alert.id),
            "device_id": str(device.id),
            "bed_id": str(device.bed_id),
            "location": location,
            "type": payload.type.value,
            "created_at": alert.created_at.isoformat(),
        },
    )
    logger.info(
        "alert %s type=%s bed=%s pushed_to=%d",
        alert.id,
        payload.type.value,
        device.bed_id,
        sent,
    )
    return alert
