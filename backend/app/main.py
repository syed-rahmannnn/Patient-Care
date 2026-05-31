import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app import reminder_poller
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Role, User
from app.routes import (
    alerts,
    auth,
    beds,
    dashboard,
    fcm,
    gateway,
    messages,
    nurses,
    reminders,
    rooms,
    ws,
)
from app.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

settings = get_settings()


async def _bootstrap_admin() -> None:
    async with SessionLocal() as db:
        exists = await db.scalar(select(User.id).where(User.role == Role.admin).limit(1))
        if exists:
            return
        admin = User(
            email=settings.BOOTSTRAP_ADMIN_EMAIL.lower(),
            password_hash=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
            role=Role.admin,
            display_name="Bootstrap Admin",
        )
        db.add(admin)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # During early dev we create tables directly; Alembic is for prod migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _bootstrap_admin()
    poller_task = asyncio.create_task(reminder_poller.run())
    try:
        yield
    finally:
        poller_task.cancel()
        try:
            await poller_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        await engine.dispose()


app = FastAPI(
    title="Patient Care System",
    version="0.1.0",
    description="Real-time patient alert + caregiver coordination API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(rooms.router, prefix="/api/v1")
app.include_router(beds.router, prefix="/api/v1")
app.include_router(nurses.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(fcm.router, prefix="/api/v1")
app.include_router(gateway.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(ws.router)  # WS routes mounted at root: /ws/beds/{id}, /ws/gateway


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ===== Serve the built admin website (single-service deploy) =====
# In dev we run the Vite dev server instead; this only kicks in once `web/` has
# been built (web/dist exists). Client-side routes fall back to index.html.
_WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
_RESERVED = {"api", "ws", "health", "docs", "redoc", "openapi.json"}

if _WEB_DIST.is_dir():
    if (_WEB_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path.split("/", 1)[0] in _RESERVED:
            raise HTTPException(status_code=404, detail="not found")
        candidate = _WEB_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_WEB_DIST / "index.html")
