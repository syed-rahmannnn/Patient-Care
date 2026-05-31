import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AlertType, Role


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ===== Auth =====

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)
    role: Role = Role.nurse  # admin-only routes will validate


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class WsTicket(BaseModel):
    token: str
    expires_in: int


class UserOut(_ORM):
    id: uuid.UUID
    email: EmailStr
    role: Role
    display_name: str
    created_at: datetime


# ===== Devices =====

class DeviceCreateIn(BaseModel):
    serial_id: str = Field(min_length=3, max_length=64)
    name: str = Field(default="", max_length=120)


class DeviceOut(_ORM):
    id: uuid.UUID
    serial_id: str
    name: str
    bed_id: uuid.UUID
    created_at: datetime


class DeviceTokenOut(BaseModel):
    device_id: uuid.UUID
    serial_id: str
    token: str  # long-lived JWT for the gateway


# ===== Beds =====

class BedNurseOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    online: bool = False


class BedCreateIn(BaseModel):
    label: str = Field(default="", max_length=60)  # blank → auto "Bed N"


class BedOut(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    room_name: str
    label: str
    join_code: str
    created_at: datetime
    device: DeviceOut | None = None
    status: str = "inactive"           # "active" when a device is paired
    connected: bool = False            # gateway WebSocket currently live
    nurses: list[BedNurseOut] = []


# ===== Rooms =====

class RoomCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RoomOut(_ORM):
    id: uuid.UUID
    name: str
    created_at: datetime
    bed_count: int = 0
    active_bed_count: int = 0


class RoomDetailOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    beds: list[BedOut] = []


# ===== Join (nurse) =====

class JoinBedIn(BaseModel):
    join_code: str = Field(min_length=3, max_length=16)


# ===== Nurses (admin) =====

class NurseCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)


class NurseAssignmentOut(BaseModel):
    bed_id: uuid.UUID
    bed_label: str
    room_id: uuid.UUID
    room_name: str
    joined_at: datetime


class NurseOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: Role
    created_at: datetime
    online: bool = False
    assignments: list[NurseAssignmentOut] = []


# ===== FCM =====

class FcmTokenIn(BaseModel):
    token: str = Field(min_length=10)
    platform: str = Field(default="android", max_length=16)


# ===== Alerts =====

class AlertOut(_ORM):
    id: uuid.UUID
    device_id: uuid.UUID
    bed_id: uuid.UUID
    type: AlertType
    created_at: datetime
    acknowledged_by: uuid.UUID | None
    acknowledged_by_name: str | None = None
    acknowledged_at: datetime | None
    # Enriched for admin/website feeds:
    bed_label: str | None = None
    room_id: uuid.UUID | None = None
    room_name: str | None = None


class GatewayEventIn(BaseModel):
    type: AlertType


# ===== Reminders =====

class ReminderCreateIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    fire_at: datetime
    max_fires: int = Field(default=3, ge=1, le=10)
    interval_sec: int = Field(default=5, ge=1, le=300)


class ReminderOut(_ORM):
    id: uuid.UUID
    device_id: uuid.UUID
    message: str
    fire_at: datetime
    next_fire_at: datetime
    fired_count: int
    max_fires: int
    interval_sec: int
    cancelled: bool
    created_at: datetime


# ===== Messages (nurse → patient) =====

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class MessageOut(_ORM):
    id: uuid.UUID
    device_id: uuid.UUID
    sender_id: uuid.UUID
    text: str
    created_at: datetime
    delivered_at: datetime | None


# ===== Dashboard =====

class DashboardStatsOut(BaseModel):
    rooms: int
    beds: int
    active_beds: int          # beds with a paired device
    connected_devices: int    # gateways with a live WebSocket
    nurses_total: int
    nurses_online: int
    pending_requests: int     # unacknowledged alerts
