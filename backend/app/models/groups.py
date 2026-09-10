"""
Group Authority -- per-module security, controlled by group.

Design (confirmed with Dennis, 2026-09-10):
- A staff member belongs to exactly **one** Group *per company* they
  work in (UserCompanyAccess.group_id). Groups are themselves
  company-scoped, so someone working across two entities holds a
  separate Group in each.
- A Group's authority over a module is one of four levels:
  None / View / Edit / Full.
- This is deliberately independent of the specific-responsibility rules
  already confirmed (e.g. SRV-004/SRV-011: Nico, or Cherish as backup,
  decides excess usage) -- those stay keyed off User.role, not Group
  Authority. Group Authority governs general module access (can this
  person open Contracts at all, and can they edit vs. only view), not
  who is allowed to make a specific confirmed business decision.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccessLevel(str, enum.Enum):
    NONE = "none"
    VIEW = "view"
    EDIT = "edit"
    FULL = "full"


ACCESS_LEVEL_ORDER = {
    AccessLevel.NONE: 0,
    AccessLevel.VIEW: 1,
    AccessLevel.EDIT: 2,
    AccessLevel.FULL: 3,
}


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    authorities: Mapped[list["GroupModuleAuthority"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupModuleAuthority(Base):
    """One row per (group, module): the access level that group has on
    that module. Absence of a row means AccessLevel.NONE."""

    __tablename__ = "group_module_authorities"
    __table_args__ = (UniqueConstraint("group_id", "module_key", name="uq_group_module"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), nullable=False)
    module_key: Mapped[str] = mapped_column(ForeignKey("modules.key"), nullable=False)
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel, name="access_level"), default=AccessLevel.NONE
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    group: Mapped["Group"] = relationship(back_populates="authorities")
