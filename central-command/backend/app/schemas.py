"""Pydantic schemas for Central Command API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: str


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    full_name: str
    is_active: bool


# ── Clients ───────────────────────────────────────────────────────────
class ClientCreate(BaseModel):
    name: str
    code: str
    db_host: str
    db_port: int = 5432
    db_name: str
    db_username: str
    db_password: str
    db_use_tls: bool = True
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_username: str | None = None
    db_password: str | None = None
    db_use_tls: bool | None = None
    status: str | None = None
    notes: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str
    db_host: str
    db_port: int
    db_name: str
    db_username: str
    db_use_tls: bool
    status: str
    notes: str | None
    last_connected_at: datetime | None
    last_known_alembic_head: str | None
    created_at: datetime
    updated_at: datetime


class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str
    status: str
    last_connected_at: datetime | None
    last_known_alembic_head: str | None


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    alembic_head: str | None = None
    companies: list[dict] | None = None


# ── Advertisements ────────────────────────────────────────────────────
class AdvertisementCreate(BaseModel):
    tag: str | None = None
    text: str
    sort_order: int = 0
    is_active: bool = True
    client_ids: list[uuid.UUID] = []


class AdvertisementUpdate(BaseModel):
    tag: str | None = None
    text: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    client_ids: list[uuid.UUID] | None = None


class AdAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    client_id: uuid.UUID
    pushed_at: datetime | None


class AdvertisementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tag: str | None
    text: str
    sort_order: int
    is_active: bool
    created_at: datetime
    assignments: list[AdAssignmentOut] = []


# ── Video Settings ────────────────────────────────────────────────────
class VideoSettingCreate(BaseModel):
    video_url: str | None = None
    label: str = "Default"
    client_ids: list[uuid.UUID] = []


class VideoSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    video_url: str | None
    label: str
    is_active: bool
    created_at: datetime


# ── License Management ────────────────────────────────────────────────
class LicenseAction(BaseModel):
    """Set a module's enabled state on a client."""
    module_key: str
    enabled: bool
    license_type: str | None = None
    notes: str | None = None


class ClientModuleOut(BaseModel):
    module_key: str
    module_name: str
    enabled: bool
    license_type: str
    notes: str | None
    updated_at: datetime | None


# ── Config Updates ────────────────────────────────────────────────────
class ConfigUpdateCreate(BaseModel):
    title: str
    description: str | None = None
    sql_statement: str


class ConfigUpdateUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    sql_statement: str | None = None
    status: str | None = None


class ConfigPushLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    success: bool
    error_message: str | None
    pushed_at: datetime


class ConfigUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    sql_statement: str
    status: str
    created_at: datetime
    updated_at: datetime
    push_logs: list[ConfigPushLogOut] = []


# ── Push Logs ─────────────────────────────────────────────────────────
class PushLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    push_type: str
    detail: str
    success: bool
    error_message: str | None
    pushed_at: datetime
    pushed_by: uuid.UUID | None


# ── Dashboard ─────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_clients: int
    active_clients: int
    suspended_clients: int
    total_ads: int
    active_ads: int
    total_config_updates: int
    pending_pushes: int
    recent_pushes: list[PushLogOut]
