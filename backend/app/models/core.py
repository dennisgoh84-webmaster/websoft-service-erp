"""
Core / Administration models: Company, User, and the central Audit Log.

RBAC is split across two independent axes (confirmed with Dennis,
2026-09-10 -- resolves open item 8.4):
- `User.role` is a small fixed enum used ONLY for the specific
  named-responsibility rules already confirmed in the business rules
  (e.g. SRV-004/SRV-011: Nico, or Cherish as backup, decides excess
  usage; Dennis as owner). It does not drive general module access.
- `User.group_id` -> Group Authority (see app/models/groups.py) drives
  general per-module security: what a user can see/do in each module,
  at None/View/Edit/Full granularity, controlled by which Group they
  belong to (exactly one Group per user).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"  # Dennis
    SERVICE_LEAD = "service_lead"  # Nico
    SALES_MANAGER = "sales_manager"  # Cherish
    SUPPORT_ENGINEER = "support_engineer"
    FINANCE = "finance"


class Company(Base):
    """A legal entity using the system. Single row today (Webmaster
    Consultancy Pte Ltd); the schema anticipates more companies later
    per CLAUDE.md's multi-company architecture decision."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Singapore")
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Singapore")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    # Group Authority: exactly one Group per user, driving general
    # per-module access (independent of `role` above).
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship()
    group: Mapped["Group | None"] = relationship()  # noqa: F821


class AuditLogEntry(Base):
    """Central audit trail -- the data behind the Event Logs module (see
    app/routers/event_logs.py). Every module writes here for actions
    that must be auditable per CLAUDE.md's development rules and,
    concretely, SRV-004's requirement that excess-usage decisions
    record who decided, when, what, and why.

    `actor_name`, `ip_address`, `user_agent`, and `device_id` are a
    point-in-time snapshot taken when the entry is written (see
    app/services/audit.py) so the trail stays meaningful even if the
    actor's name later changes or their account is deactivated. Note:
    a browser cannot expose a real hardware/PC serial number for
    security reasons -- `device_id` is a random identifier the
    frontend generates once and persists in that browser's storage
    (see frontend/src/lib/deviceId.ts), which identifies "this browser
    on this machine" rather than the physical hardware.

    `old_value`/`new_value` hold a small JSON object of just the
    fields that changed (e.g. '{"role": "support_engineer"}' ->
    '{"role": "service_lead"}') for edits where a field-level diff is
    meaningful; left null for actions where it isn't (e.g. a password
    reset never records the password itself)."""

    __tablename__ = "audit_log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
