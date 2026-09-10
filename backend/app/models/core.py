"""
Core / Administration models: Company, User, and the central Audit Log.

RBAC here is intentionally minimal (a single `role` field) -- the
detailed role/permission catalogue is still an open business decision
(see docs/open-business-decisions.md, item 8.4). This is enough to
support the named responsibilities already confirmed in the business
rules (Dennis as owner, Nico as Service & Support lead, Cherish as
Sales Manager / backup reviewer).
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
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship()


class AuditLogEntry(Base):
    """Central audit trail. Every module writes here for actions that
    must be auditable per CLAUDE.md's development rules and, concretely,
    SRV-004's requirement that excess-usage decisions record who
    decided, when, what, and why."""

    __tablename__ = "audit_log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
