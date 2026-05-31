import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_admin
from app.models import Role, User
from app.schemas import NurseCreateIn, NurseOut
from app.security import hash_password
from app.serializers import build_nurse_out

router = APIRouter(prefix="/nurses", tags=["nurses"])


@router.get("", response_model=list[NurseOut])
async def list_nurses(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> list[NurseOut]:
    nurses = list(
        await db.scalars(
            select(User).where(User.role == Role.nurse).order_by(User.display_name, User.email)
        )
    )
    return [await build_nurse_out(db, n) for n in nurses]


@router.post("", response_model=NurseOut, status_code=status.HTTP_201_CREATED)
async def create_nurse(
    payload: NurseCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> NurseOut:
    display = payload.display_name.strip() or payload.email.split("@")[0]
    nurse = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=Role.nurse,
        display_name=display,
    )
    db.add(nurse)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "that email is already in use") from e
    await db.refresh(nurse)
    return await build_nurse_out(db, nurse)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nurse(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> None:
    nurse = await db.scalar(select(User).where(User.id == user_id, User.role == Role.nurse))
    if not nurse:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "nurse not found")
    await db.delete(nurse)  # cascades memberships / fcm tokens
    await db.commit()
