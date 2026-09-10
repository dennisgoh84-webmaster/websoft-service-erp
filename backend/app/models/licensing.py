"""
Module Control / multi-company licensing -- Core / Administration.

`Module` is a fixed catalog of the business areas from
docs/module-map.md (CRM, Sales, Service Contracts, Billing, etc.).
`CompanyModule` says whether a given company has a given module
enabled/licensed. This is deliberately lightweight (a flag + a license
type label, not seat counts, expiry, or billing integration) -- it
exists to give Dennis a single place to control which modules are
active per company, ahead of the multi-company future in CLAUDE.md's
approved architecture. A module being enabled here does not by itself
mean it has application code yet (see `Module.is_built`).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LicenseType(str, enum.Enum):
    INCLUDED = "included"  # bundled with the base subscription
    ADD_ON = "add_on"  # separately licensed
    TRIAL = "trial"  # time-limited, no expiry tracking yet


class Module(Base):
    """Fixed catalog of business-area modules (docs/module-map.md)."""

    __tablename__ = "modules"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_built: Mapped[bool] = mapped_column(Boolean, default=False)  # has application code yet


class CompanyModule(Base):
    """Per-company module enablement/license. One row per (company, module)."""

    __tablename__ = "company_modules"
    __table_args__ = (UniqueConstraint("company_id", "module_key", name="uq_company_module"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    module_key: Mapped[str] = mapped_column(ForeignKey("modules.key"), nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    license_type: Mapped[LicenseType] = mapped_column(
        Enum(LicenseType, name="license_type"), default=LicenseType.INCLUDED
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    module: Mapped["Module"] = relationship()
