import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_admin, current_user
from app.models import Role, User
from app.schemas import (
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UserOut,
    WsTicket,
)
from app.security import (
    decode_token,
    hash_password,
    make_access_token,
    make_refresh_token,
    make_ws_ticket,
    verify_password,
)
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(current_admin),
) -> User:
    """Admin-only after the bootstrap admin is created. Use to provision nurses (and other admins)."""
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        display_name=payload.display_name,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "email already in use") from e
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenPair(
        access_token=make_access_token(user.id, user.role.value),
        refresh_token=make_refresh_token(user.id),
    )


# Form-encoded token endpoint so the Swagger UI "Authorize" button works.
# Maps `username` → email; the Flutter app keeps using JSON `/login`.
@router.post("/token", response_model=TokenPair, include_in_schema=False)
async def token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenPair(
        access_token=make_access_token(user.id, user.role.value),
        refresh_token=make_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        data = decode_token(payload.refresh_token)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    if data.get("typ") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not a refresh token")
    user = await db.scalar(select(User).where(User.id == uuid.UUID(data["sub"])))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return TokenPair(
        access_token=make_access_token(user.id, user.role.value),
        refresh_token=make_refresh_token(user.id),
    )


@router.post("/ws-ticket", response_model=WsTicket)
async def ws_ticket(user: User = Depends(current_user)) -> WsTicket:
    return WsTicket(token=make_ws_ticket(user.id), expires_in=settings.WS_TICKET_TTL_SEC)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user


# Public, unauthed "is there any admin yet?" probe lets a client decide whether
# to show the bootstrap flow. Keeps the bootstrap path explicit rather than
# silently magicking the first user into an admin.
@router.get("/has-admin")
async def has_admin(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    row = await db.scalar(select(User.id).where(User.role == Role.admin).limit(1))
    return {"has_admin": row is not None}
