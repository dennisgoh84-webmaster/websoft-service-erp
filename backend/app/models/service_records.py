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

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
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

    work_date: Mapped[date] = mapped_column(nullable=False)
    raw_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    rounded_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # SRV-007

    status: Mapped[ServiceRecordStatus] = mapped_column(
        Enum(ServiceRecordStatus, name="service_record_status"), default=ServiceRecordStatus.SUBMITTED
    )
    outcome: Mapped[ServiceRecordOutcome] = mapped_column(
        Enum(ServiceRecordOutcome, name="service_record_outcome"), default=ServiceRecordOutcome.PENDING
    )

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
