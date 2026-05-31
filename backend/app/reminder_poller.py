import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.fcm import fan_out
from app.models import BedMembership, Device, Reminder
from app.ws_manager import hub

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 15


async def _fire_one(reminder: Reminder) -> None:
    async with SessionLocal() as db:
        device = await db.scalar(select(Device).where(Device.id == reminder.device_id))
        if not device:
            return
        nurse_ids = list(
            await db.scalars(
                select(BedMembership.user_id).where(BedMembership.bed_id == device.bed_id)
            )
        )
        await fan_out(
            db,
            nurse_ids,
            title="⏰ Reminder",
            body=reminder.message,
            data={
                "kind": "reminder.fire",
                "reminder_id": str(reminder.id),
                "device_id": str(device.id),
                "bed_id": str(device.bed_id),
                "message": reminder.message,
            },
        )
        await hub.broadcast_bed(
            device.bed_id,
            {
                "event": "reminder.fire",
                "reminder_id": str(reminder.id),
                "device_id": str(device.id),
                "message": reminder.message,
                "fired_count": reminder.fired_count + 1,
                "max_fires": reminder.max_fires,
            },
        )
        await hub.send_to_gateway(
            device.id,
            {"kind": "REM", "message": reminder.message},
        )

        # advance state
        reminder.fired_count += 1
        if reminder.fired_count >= reminder.max_fires:
            reminder.next_fire_at = reminder.next_fire_at  # leave as-is; query filter excludes
        else:
            reminder.next_fire_at = datetime.now(timezone.utc) + timedelta(seconds=reminder.interval_sec)
        db.add(reminder)
        await db.commit()


async def _tick() -> None:
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        due = list(
            await db.scalars(
                select(Reminder).where(
                    Reminder.next_fire_at <= now,
                    Reminder.cancelled.is_(False),
                    Reminder.fired_count < Reminder.max_fires,
                )
            )
        )
    for r in due:
        try:
            await _fire_one(r)
        except Exception as e:  # noqa: BLE001
            logger.exception("reminder %s fire failed: %s", r.id, e)


async def run() -> None:
    logger.info("reminder poller started (every %ds)", POLL_INTERVAL_SEC)
    while True:
        try:
            await _tick()
        except Exception as e:  # noqa: BLE001
            logger.exception("reminder tick failed: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SEC)
