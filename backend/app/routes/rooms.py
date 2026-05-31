import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes import new_join_code
from app.db import get_db
from app.deps import current_admin
from app.models import Bed, Device, Room, User
from app.schemas import BedCreateIn, BedOut, RoomCreateIn, RoomDetailOut, RoomOut
from app.serializers import build_bed_out

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _room_out(db: AsyncSession, room: Room) -> RoomOut:
    bed_count = await db.scalar(select(func.count(Bed.id)).where(Bed.room_id == room.id)) or 0
    active = (
        await db.scalar(
            select(func.count(func.distinct(Device.bed_id)))
            .select_from(Bed)
            .join(Device, Device.bed_id == Bed.id)
            .where(Bed.room_id == room.id)
        )
        or 0
    )
    out = RoomOut.model_validate(room)
    out.bed_count = int(bed_count)
    out.active_bed_count = int(active)
    return out


def _next_bed_label(existing: list[str]) -> str:
    used = set(existing)
    i = 1
    while f"Bed {i}" in used:
        i += 1
    return f"Bed {i}"


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> RoomOut:
    room = Room(name=payload.name.strip(), created_by=admin.id)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return await _room_out(db, room)


@router.get("", response_model=list[RoomOut])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> list[RoomOut]:
    rooms = list(await db.scalars(select(Room).order_by(Room.created_at)))
    return [await _room_out(db, r) for r in rooms]


@router.get("/{room_id}", response_model=RoomDetailOut)
async def get_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> RoomDetailOut:
    room = await db.scalar(select(Room).where(Room.id == room_id))
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "room not found")
    beds = list(await db.scalars(select(Bed).where(Bed.room_id == room.id).order_by(Bed.created_at)))
    bed_outs = [await build_bed_out(db, b, room_name=room.name) for b in beds]
    return RoomDetailOut(id=room.id, name=room.name, created_at=room.created_at, beds=bed_outs)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> None:
    room = await db.scalar(select(Room).where(Room.id == room_id))
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "room not found")
    await db.delete(room)  # cascades to beds → devices / memberships
    await db.commit()


@router.post("/{room_id}/beds", response_model=BedOut, status_code=status.HTTP_201_CREATED)
async def create_bed(
    room_id: uuid.UUID,
    payload: BedCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> BedOut:
    room = await db.scalar(select(Room).where(Room.id == room_id))
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "room not found")

    existing = list(await db.scalars(select(Bed.label).where(Bed.room_id == room.id)))
    label = payload.label.strip() or _next_bed_label(existing)
    if label in existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "a bed with that label already exists in this room")

    for _ in range(5):  # retry on the (rare) join-code collision
        bed = Bed(room_id=room.id, label=label, join_code=new_join_code(), created_by=admin.id)
        db.add(bed)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(bed)
        return await build_bed_out(db, bed, room_name=room.name)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "could not allocate a join code")
