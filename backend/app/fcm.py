import json
import logging
from typing import Iterable

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import FcmToken

logger = logging.getLogger(__name__)
settings = get_settings()

_initialized = False


def _init() -> bool:
    global _initialized
    if _initialized:
        return True
    if not settings.FIREBASE_CREDS_JSON.strip():
        return False
    try:
        cred_data = json.loads(settings.FIREBASE_CREDS_JSON)
        cred = credentials.Certificate(cred_data)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("firebase-admin initialized")
        return True
    except Exception as e:
        logger.error("firebase-admin init failed: %s", e)
        return False


async def fan_out(
    db: AsyncSession,
    user_ids: Iterable[str],
    *,
    title: str,
    body: str,
    data: dict[str, str],
    high_priority: bool = False,
) -> int:
    """Send a data-only FCM push to every token owned by these users.

    Returns the number of successful deliveries. Stale tokens are deleted
    from the DB on UNREGISTERED.
    """
    user_id_list = list(user_ids)
    if not user_id_list:
        return 0

    tokens = list(
        await db.scalars(select(FcmToken.token).where(FcmToken.user_id.in_(user_id_list)))
    )
    if not tokens:
        return 0

    # Data-only payload — Flutter renders via flutter_local_notifications so we
    # control the channel/priority/bypassDnd locally.
    payload_data = {**data, "title": title, "body": body}

    if not _init():
        logger.info(
            "FCM not configured; would have sent to %d tokens (title=%r data=%r)",
            len(tokens),
            title,
            payload_data,
        )
        return 0

    android = messaging.AndroidConfig(
        priority="high" if high_priority else "normal",
        ttl=60,
    )
    message = messaging.MulticastMessage(
        tokens=tokens,
        data=payload_data,
        android=android,
    )
    resp = messaging.send_each_for_multicast(message)

    stale: list[str] = []
    for idx, r in enumerate(resp.responses):
        if r.success:
            continue
        if r.exception and getattr(r.exception, "code", "") in {
            "UNREGISTERED",
            "registration-token-not-registered",
        }:
            stale.append(tokens[idx])
    if stale:
        await db.execute(delete(FcmToken).where(FcmToken.token.in_(stale)))
        await db.commit()
        logger.info("purged %d stale FCM tokens", len(stale))

    return resp.success_count
