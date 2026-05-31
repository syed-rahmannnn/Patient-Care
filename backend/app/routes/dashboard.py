from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_admin
from app.models import Alert, Bed, Device, Role, Room, User
from app.schemas import AlertOut, DashboardStatsOut
from app.ws_manager import hub

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
async def stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> DashboardStatsOut:
    rooms = await db.scalar(select(func.count(Room.id))) or 0
    beds = await db.scalar(select(func.count(Bed.id))) or 0
    active_beds = await db.scalar(select(func.count(func.distinct(Device.bed_id)))) or 0
    nurses_total = await db.scalar(select(func.count(User.id)).where(User.role == Role.nurse)) or 0
    pending = await db.scalar(select(func.count(Alert.id)).where(Alert.acknowledged_by.is_(None))) or 0

    nurse_ids = {str(x) for x in await db.scalars(select(User.id).where(User.role == Role.nurse))}
    nurses_online = len(hub.online_user_ids() & nurse_ids)

    return DashboardStatsOut(
        rooms=int(rooms),
        beds=int(beds),
        active_beds=int(active_beds),
        connected_devices=len(hub.connected_device_ids()),
        nurses_total=int(nurses_total),
        nurses_online=nurses_online,
        pending_requests=int(pending),
    )


@router.get("/requests", response_model=list[AlertOut])
async def recent_requests(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
    limit: int = Query(20, ge=1, le=200),
) -> list[AlertOut]:
    acked = User.__table__.alias("acked")
    rows = (
        await db.execute(
            select(Alert, Bed.label, Room.id, Room.name, acked.c.display_name, acked.c.email)
            .join(Bed, Bed.id == Alert.bed_id)
            .join(Room, Room.id == Bed.room_id)
            .outerjoin(acked, acked.c.id == Alert.acknowledged_by)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
    ).all()
    out: list[AlertOut] = []
    for alert, bed_label, room_id, room_name, ack_name, ack_email in rows:
        item = AlertOut.model_validate(alert)
        item.bed_label = bed_label
        item.room_id = room_id
        item.room_name = room_name
        if alert.acknowledged_by:
            item.acknowledged_by_name = (ack_name or ack_email or "").strip() or None
        out.append(item)
    return out
