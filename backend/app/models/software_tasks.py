"""Software Task -- confirmed 2026-09-10 as a minimal first slice
(Dennis: "enough for a start, we can extend again later"): a task a
programmer enters, assigned to a programmer, noting which
modules/reports it affects, a target programming-finish date, manually
keyed programming hours, and who it's assigned to for testing. Used by
both the Support Monitoring dashboard (as "Un-Test S/T" -- a task
assigned for testing but not yet tested) and the future Software
Development area (docs/open-business-decisions.md #12.1-12.3).

No status workflow beyond `is_tested` is modeled yet -- deliberately
minimal pending real usage, per Dennis's note above.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SoftwareTask(Base):
    __tablename__ = "software_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free text -- which module(s)/report(s) this task touches. No
    # formal software-module catalog exists in this system.
    modules_affected: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assigned_programmer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    programming_finish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Manually keyed, not derived from any time-logging (no timesheet
    # concept for programming work exists here, unlike Service Records
    # for support hours).
    programming_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    tester_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_tested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
