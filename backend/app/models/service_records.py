"""Service Records (formerly "Timesheets"), implementing SRV-007
(15-min rounding) and SRV-015 (3-business-day submission deadline).

Who approves a Service Record, and within what timeframe, remains an
open business decision (docs/open-business-decisions.md, item 9.1),
currently deferred at the user's request. For this build, any user with
role service_lead, sales_manager, or owner can approve -- a pragmatic
default, not a business rule, and clearly revisable once 9.1 is decided.
"""
import enum
import math
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.contracts import HOUR_ROUNDING_MINUTES


class ServiceRecordStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"


class ServiceRecordOutcome(str, enum.Enum):
    PENDING = "pending"  # not yet approved / processed
    CONTRACT_DEDUCTION = "contract_deduction"  # SRV-003: hours remained
    EXCESS_USAGE = "excess_usage"  # SRV-003/004: hours were exhausted
    # Work approved under an ANNUAL (term-only) contract -- confirmed
    # 2026-09-10. There is no hour pool to deduct from or exceed.
    NOT_HOUR_METERED = "not_hour_metered"


class ServiceRecordCompletion(str, enum.Enum):
    """Set by whoever submits the record (confirmed 2026-09-11): does
    this work session finish the Job Order, or will there be another
    visit? Drives Job Order auto-close -- see
    app/services/service_records.py maybe_auto_close_job_order()."""

    COMPLETED = "C"
    UNCOMPLETED = "U"


def round_up_to_nearest(minutes: int, increment: int = HOUR_ROUNDING_MINUTES) -> int:
    """SRV-007: round a logged-time entry up to the nearest 15 minutes."""
    if minutes <= 0:
        return 0
    return math.ceil(minutes / increment) * increment


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Multi-company: inherited from the job order this work was logged
    # against, so service records filter by company directly.
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    job_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_orders.id"), nullable=False)
    employee_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # System-generated running number (confirmed 2026-09-11 -- "all main
    # documents need to have a system generated running number to be
    # controlled"), same SR-<year>-<seq> pattern as every other document.
    service_record_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    work_date: Mapped[date] = mapped_column(nullable=False)
    raw_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    rounded_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # SRV-007

    status: Mapped[ServiceRecordStatus] = mapped_column(
        Enum(ServiceRecordStatus, name="service_record_status"), default=ServiceRecordStatus.SUBMITTED
    )
    outcome: Mapped[ServiceRecordOutcome] = mapped_column(
        Enum(ServiceRecordOutcome, name="service_record_outcome"), default=ServiceRecordOutcome.PENDING
    )
    # Set by the submitter -- does this session finish the job, or will
    # someone come back? Drives Job Order auto-close (confirmed
    # 2026-09-11, see app/services/service_records.py).
    completion_status: Mapped[ServiceRecordCompletion] = mapped_column(
        Enum(ServiceRecordCompletion, name="service_record_completion"),
        default=ServiceRecordCompletion.UNCOMPLETED,
        nullable=False,
    )
    # "After Office Hrs/Weekend/Holiday X2.0" (confirmed 2026-09-11) --
    # manual, set by the submitter (no office-hours/public-holiday
    # calendar exists in this build to derive it from). Feeds the
    # suggested deduction-minutes multiplier at approval time only; it
    # never changes raw_minutes/rounded_minutes.
    is_after_hours: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The minutes actually deducted from the contract's hour pool, keyed
    # in by the approver (confirmed 2026-09-11: "actual is 240mins,
    # deducted is 220mins or 360mins") -- distinct from rounded_minutes,
    # which stays the objective SRV-007 log. Null until approved; the
    # approval form prefills a suggestion (rounded_minutes x the
    # applicable Urgent/after-hours multiplier) but the approver can
    # type any value.
    deducted_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Work description (2026-09-12): free text describing what was done
    # this session -- previously there was no such field at all. Optional,
    # not previously required, so this doesn't retroactively invalidate
    # any existing record. Spellchecked in the browser as the submitter
    # types it (see frontend/src/pages/JobOrderDetailPage.tsx) -- browser-
    # native only, no AI/external service call (confirmed with Dennis,
    # 2026-09-12, docs/open-business-decisions.md #35).
    work_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mobile web app time tracking (2026-09-12, planned-work.md #1):
    # replaces manual minutes entry when used from mobile. Minutes are
    # auto-computed from time_out - time_in. If only time_in is set
    # (staff forgot to tap Time Out), the record stays open until they do.
    time_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    job_order: Mapped["JobOrder"] = relationship()  # noqa: F821

    @property
    def is_late(self) -> bool:
        """SRV-015: flagged missing if not submitted within 3 business
        days of the work being performed. (Business-day precision is a
        future refinement; this demo uses calendar days.)"""
        from app.models.contracts import SERVICE_RECORD_SUBMISSION_DEADLINE_DAYS

        return (self.submitted_at.date() - self.work_date).days > SERVICE_RECORD_SUBMISSION_DEADLINE_DAYS
