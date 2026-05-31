import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes import new_join_code
from app.db import get_db
from app.deps import current_admin, current_user
from app.models import Alert, Bed, BedMembership, Device, Role, Room, User
from app.schemas import (
    AlertOut,
    BedOut,
    DeviceCreateIn,
    DeviceTokenOut,
    JoinBedIn,
)
from app.security import make_device_token
from app.serializers import build_bed_out

router = APIRouter(prefix="/beds", tags=["beds"])


async def _get_bed(db: AsyncSession, bed_id: uuid.UUID) -> Bed:
    bed = await db.scalar(select(Bed).where(Bed.id == bed_id))
    if not bed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bed not found")
    return bed


async def _ensure_can_view(db: AsyncSession, bed: Bed, user: User) -> None:
    if user.role == Role.admin:
        return
    member = await db.scalar(
        select(BedMembership.id).where(
            BedMembership.bed_id == bed.id, BedMembership.user_id == user.id
        )
    )
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this bed")


# ===== Nurse flows (static paths first so they aren't parsed as a bed_id) =====

@router.get("/me", response_model=list[BedOut])
async def my_beds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> list[BedOut]:
    beds = list(
        await db.scalars(
            select(Bed)
            .join(BedMembership, BedMembership.bed_id == Bed.id)
            .where(BedMembership.user_id == user.id)
            .order_by(Bed.created_at)
        )
    )
    return [await build_bed_out(db, b) for b in beds]


@router.post("/join", response_model=BedOut)
async def join_bed(
    payload: JoinBedIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> BedOut:
    code = payload.join_code.strip().upper()
    bed = await db.scalar(select(Bed).where(Bed.join_code == code))
    if not bed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "invalid join code")
    db.add(BedMembership(bed_id=bed.id, user_id=user.id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # already a member — idempotent
    return await build_bed_out(db, bed)


# ===== Bed detail / membership =====

@router.get("/{bed_id}", response_model=BedOut)
async def get_bed(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> BedOut:
    bed = await _get_bed(db, bed_id)
    await _ensure_can_view(db, bed, user)
    return await build_bed_out(db, bed)


@router.delete("/{bed_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_bed(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    await db.execute(
        delete(BedMembership).where(
            BedMembership.bed_id == bed_id, BedMembership.user_id == user.id
        )
    )
    await db.commit()


@router.get("/{bed_id}/alerts", response_model=list[AlertOut])
async def list_bed_alerts(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[AlertOut]:
    bed = await _get_bed(db, bed_id)
    await _ensure_can_view(db, bed, user)
    room_name = await db.scalar(select(Room.name).where(Room.id == bed.room_id))
    rows = (
        await db.execute(
            select(Alert, User.display_name, User.email)
            .outerjoin(User, User.id == Alert.acknowledged_by)
            .where(Alert.bed_id == bed_id)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
    ).all()
    out: list[AlertOut] = []
    for alert, name, email in rows:
        item = AlertOut.model_validate(alert)
        item.bed_label = bed.label
        item.room_id = bed.room_id
        item.room_name = room_name
        if alert.acknowledged_by:
            item.acknowledged_by_name = (name or email or "").strip() or None
        out.append(item)
    return out


# ===== Admin: code + device management =====

@router.post("/{bed_id}/regenerate-code", response_model=BedOut)
async def regenerate_code(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> BedOut:
    bed = await _get_bed(db, bed_id)
    for _ in range(5):
        bed.join_code = new_join_code()
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(bed)
        return await build_bed_out(db, bed)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "could not allocate a join code")


@router.delete("/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bed(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> None:
    bed = await _get_bed(db, bed_id)
    await db.delete(bed)  # cascades to device + memberships + alerts
    await db.commit()


@router.post("/{bed_id}/device", response_model=DeviceTokenOut, status_code=status.HTTP_201_CREATED)
async def pair_device(
    bed_id: uuid.UUID,
    payload: DeviceCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> DeviceTokenOut:
    bed = await _get_bed(db, bed_id)
    # A bed holds one device — replace any existing pairing.
    await db.execute(delete(Device).where(Device.bed_id == bed.id))
    device = Device(serial_id=payload.serial_id.strip(), name=payload.name or payload.serial_id, bed_id=bed.id)
    db.add(device)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "that serial id is already paired to another bed") from e
    await db.refresh(device)
    return DeviceTokenOut(
        device_id=device.id,
        serial_id=device.serial_id,
        token=make_device_token(device.id, device.serial_id),
    )


@router.delete("/{bed_id}/device", status_code=status.HTTP_204_NO_CONTENT)
async def unpair_device(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> None:
    await _get_bed(db, bed_id)
    await db.execute(delete(Device).where(Device.bed_id == bed_id))
    await db.commit()
