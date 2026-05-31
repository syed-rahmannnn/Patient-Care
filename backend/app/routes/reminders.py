import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user
from app.models import BedMembership, Device, Reminder, Role, User
from app.schemas import ReminderCreateIn, ReminderOut

router = APIRouter(tags=["reminders"])


async def _ensure_bed_member(db: AsyncSession, device_id: uuid.UUID, user: User) -> Device:
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
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this device's bed")
    return device


@router.post("/devices/{device_id}/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    device_id: uuid.UUID,
    payload: ReminderCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Reminder:
    device = await _ensure_bed_member(db, device_id, user)
    fire_at = payload.fire_at
    if fire_at.tzinfo is None:
        fire_at = fire_at.replace(tzinfo=timezone.utc)
    reminder = Reminder(
        device_id=device.id,
        created_by=user.id,
        message=payload.message,
        fire_at=fire_at,
        next_fire_at=fire_at,
        max_fires=payload.max_fires,
        interval_sec=payload.interval_sec,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.get("/devices/{device_id}/reminders", response_model=list[ReminderOut])
async def list_reminders(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Reminder]:
    await _ensure_bed_member(db, device_id, user)
    rows = await db.scalars(
        select(Reminder)
        .where(Reminder.device_id == device_id, Reminder.cancelled.is_(False))
        .order_by(Reminder.next_fire_at.asc())
    )
    return list(rows)


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    reminder = await db.scalar(select(Reminder).where(Reminder.id == reminder_id))
    if not reminder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "reminder not found")
    await _ensure_bed_member(db, reminder.device_id, user)
    reminder.cancelled = True
    await db.commit()


@router.delete("/devices/{device_id}/reminders", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_all(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    await _ensure_bed_member(db, device_id, user)
    await db.execute(
        update(Reminder).where(Reminder.device_id == device_id).values(cancelled=True)
    )
    await db.commit()
