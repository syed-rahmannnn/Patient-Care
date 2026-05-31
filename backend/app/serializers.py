"""Builders for the enriched payloads the website/app consume.

Kept out of the route modules so rooms / beds / nurses share one source of
truth for how a bed or nurse is shaped (device, live status, members, etc.).
Query volumes here are tiny (a ward has a handful of rooms/beds), so plain
per-entity queries are fine.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bed, BedMembership, Device, Room, User
from app.schemas import (
    BedNurseOut,
    BedOut,
    DeviceOut,
    NurseAssignmentOut,
    NurseOut,
)
from app.ws_manager import hub


async def build_bed_out(db: AsyncSession, bed: Bed, *, room_name: str | None = None) -> BedOut:
    device = await db.scalar(select(Device).where(Device.bed_id == bed.id))
    device_out = DeviceOut.model_validate(device) if device else None
    connected = hub.is_gateway_connected(device.id) if device else False

    nurse_rows = await db.scalars(
        select(User)
        .join(BedMembership, BedMembership.user_id == User.id)
        .where(BedMembership.bed_id == bed.id)
        .order_by(User.display_name, User.email)
    )
    nurses = [
        BedNurseOut(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            online=hub.is_user_online(u.id),
        )
        for u in nurse_rows
    ]

    if room_name is None:
        room_name = (await db.scalar(select(Room.name).where(Room.id == bed.room_id))) or ""

    return BedOut(
        id=bed.id,
        room_id=bed.room_id,
        room_name=room_name,
        label=bed.label,
        join_code=bed.join_code,
        created_at=bed.created_at,
        device=device_out,
        status="active" if device_out else "inactive",
        connected=connected,
        nurses=nurses,
    )


async def build_nurse_out(db: AsyncSession, user: User) -> NurseOut:
    rows = (
        await db.execute(
            select(BedMembership, Bed, Room)
            .join(Bed, Bed.id == BedMembership.bed_id)
            .join(Room, Room.id == Bed.room_id)
            .where(BedMembership.user_id == user.id)
            .order_by(BedMembership.joined_at)
        )
    ).all()
    assignments = [
        NurseAssignmentOut(
            bed_id=bed.id,
            bed_label=bed.label,
            room_id=room.id,
            room_name=room.name,
            joined_at=membership.joined_at,
        )
        for membership, bed, room in rows
    ]
    return NurseOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
        online=hub.is_user_online(user.id),
        assignments=assignments,
    )
