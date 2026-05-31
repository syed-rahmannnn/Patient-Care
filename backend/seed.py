"""Seed demo data for the Patient Care System.

Idempotent — safe to run repeatedly. Creates the admin (if missing), a set of
nurse logins, a few rooms each with two beds, pairs one demo device to
Room 101 · Bed 1 (the "active" bed), assigns some nurses, and adds a handful of
sample requests so the dashboard has content.

Run from the backend/ directory with the project venv active:
    python seed.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.codes import new_join_code
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import (
    Alert,
    AlertType,
    Bed,
    BedMembership,
    Device,
    Role,
    Room,
    User,
)
from app.security import hash_password, make_device_token

settings = get_settings()

PASSWORD = "Test1234!"
NURSES = [
    ("nurse1@patient.care", "Nurse One"),
    ("nurse2@patient.care", "Nurse Two"),
    ("nurse3@patient.care", "Nurse Three"),
    ("nurse4@patient.care", "Nurse Four"),
    ("nurse5@patient.care", "Nurse Five"),
]
ROOMS = ["Room 101", "Room 102", "Room 103"]
BEDS_PER_ROOM = ["Bed 1", "Bed 2"]
DEMO_SERIAL = "PCS-DEMO-01"


async def get_or_create_user(db, email: str, display: str, role: Role) -> User:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user:
        return user
    user = User(
        email=email.lower(),
        password_hash=hash_password(PASSWORD),
        role=role,
        display_name=display,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_room(db, name: str, created_by) -> Room:
    room = await db.scalar(select(Room).where(Room.name == name))
    if room:
        return room
    room = Room(name=name, created_by=created_by)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def get_or_create_bed(db, room: Room, label: str, created_by) -> Bed:
    bed = await db.scalar(select(Bed).where(Bed.room_id == room.id, Bed.label == label))
    if bed:
        return bed
    bed = Bed(room_id=room.id, label=label, join_code=new_join_code(), created_by=created_by)
    db.add(bed)
    await db.commit()
    await db.refresh(bed)
    return bed


async def ensure_membership(db, bed: Bed, user: User) -> None:
    exists = await db.scalar(
        select(BedMembership.id).where(
            BedMembership.bed_id == bed.id, BedMembership.user_id == user.id
        )
    )
    if not exists:
        db.add(BedMembership(bed_id=bed.id, user_id=user.id))
        await db.commit()


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        admin = await get_or_create_user(
            db, settings.BOOTSTRAP_ADMIN_EMAIL, "Administrator", Role.admin
        )
        nurses = [await get_or_create_user(db, e, n, Role.nurse) for e, n in NURSES]

        rooms: list[Room] = []
        beds_by_room: dict[str, list[Bed]] = {}
        for name in ROOMS:
            room = await get_or_create_room(db, name, admin.id)
            rooms.append(room)
            beds_by_room[name] = [
                await get_or_create_bed(db, room, label, admin.id) for label in BEDS_PER_ROOM
            ]

        # Pair the one demo device to Room 101 · Bed 1 → that bed shows "active".
        bed_101_1 = beds_by_room["Room 101"][0]
        device = await db.scalar(select(Device).where(Device.serial_id == DEMO_SERIAL))
        if not device:
            device = Device(serial_id=DEMO_SERIAL, name="Bed 1 Call Device", bed_id=bed_101_1.id)
            db.add(device)
            await db.commit()
            await db.refresh(device)
        device_token = make_device_token(device.id, device.serial_id)

        # Assign nurses to beds (leaves nurse3 & nurse5 unassigned for variety).
        await ensure_membership(db, bed_101_1, nurses[0])               # nurse1 → 101/Bed1
        await ensure_membership(db, beds_by_room["Room 102"][0], nurses[1])  # nurse2 → 102/Bed1
        await ensure_membership(db, beds_by_room["Room 103"][1], nurses[3])  # nurse4 → 103/Bed2

        # Sample requests on the active bed (only if none exist yet).
        existing = await db.scalar(select(func.count(Alert.id)).where(Alert.bed_id == bed_101_1.id))
        if not existing:
            now = datetime.now(timezone.utc)
            samples = [
                (AlertType.WATER, 2, None),
                (AlertType.MEDICINE, 9, nurses[0]),
                (AlertType.HELP, 21, nurses[0]),
                (AlertType.BATHROOM, 40, nurses[0]),
            ]
            for atype, mins_ago, acked_by in samples:
                created = now - timedelta(minutes=mins_ago)
                db.add(
                    Alert(
                        device_id=device.id,
                        bed_id=bed_101_1.id,
                        type=atype,
                        created_at=created,
                        acknowledged_by=acked_by.id if acked_by else None,
                        acknowledged_at=(created + timedelta(seconds=30)) if acked_by else None,
                    )
                )
            await db.commit()

        # ---- summary ----
        print("\n=== SEED COMPLETE ===")
        print(f"Admin login : {admin.email} / {PASSWORD}")
        print(f"Nurse logins: {', '.join(n.email for n in nurses)}  (password: {PASSWORD})")
        print("\nRooms & beds (join codes):")
        for name in ROOMS:
            for bed in beds_by_room[name]:
                tag = "  [ACTIVE — demo device]" if bed.id == bed_101_1.id else ""
                print(f"  {name} · {bed.label} → {bed.join_code}{tag}")
        print(f"\nDemo device serial: {DEMO_SERIAL}")
        print("Gateway DEVICE_TOKEN (paste into gateway/.env):")
        print(device_token)
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
