import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user
from app.fcm import fan_out
from app.models import Alert, BedMembership, Role, User
from app.schemas import AlertOut
from app.ws_manager import hub

router = APIRouter(tags=["alerts"])


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def acknowledge(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> Alert:
    alert = await db.scalar(select(Alert).where(Alert.id == alert_id))
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "alert not found")

    if user.role != Role.admin:
        is_member = await db.scalar(
            select(BedMembership.id).where(
                BedMembership.bed_id == alert.bed_id, BedMembership.user_id == user.id
            )
        )
        if not is_member:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this bed")

    if alert.acknowledged_by:
        return alert  # idempotent — first ack wins

    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)

    # Live update to everyone watching this bed.
    await hub.broadcast_bed(
        alert.bed_id,
        {
            "event": "alert.ack",
            "alert_id": str(alert.id),
            "by_user_id": str(user.id),
            "by_name": user.display_name or user.email,
        },
    )
    # Silent FCM so other phones can dismiss the local notification.
    other_nurse_ids = list(
        await db.scalars(
            select(BedMembership.user_id).where(
                BedMembership.bed_id == alert.bed_id,
                BedMembership.user_id != user.id,
            )
        )
    )
    await fan_out(
        db,
        other_nurse_ids,
        title="",
        body="",
        data={
            "kind": "alert.ack",
            "alert_id": str(alert.id),
            "by_name": user.display_name or user.email,
        },
    )
    # Tell the gateway to silence the patient-side (if it ever uses ACK).
    await hub.send_to_gateway(alert.device_id, {"kind": "ACK", "alert_id": str(alert.id)})
    return alert
