from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user
from app.models import FcmToken, User
from app.schemas import FcmTokenIn

router = APIRouter(prefix="/me/fcm-tokens", tags=["fcm"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_token(
    payload: FcmTokenIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    existing = await db.scalar(select(FcmToken).where(FcmToken.token == payload.token))
    if existing:
        existing.user_id = user.id
        existing.platform = payload.platform
        await db.commit()
        return
    db.add(FcmToken(user_id=user.id, token=payload.token, platform=payload.platform))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # racy duplicate — fine, the row is there now


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    await db.execute(
        delete(FcmToken).where(FcmToken.user_id == user.id, FcmToken.token == token)
    )
    await db.commit()
