"""Job Orders (formerly "Helpdesk Tickets") -- Service Operations models.

SLA targets are explicitly deferred (SRV-009) -- priority is tracked but
no automatic response/resolution time target is computed from it.
Instead, confirmed 2026-09-10: `due_date` is a manual field, set by
whoever opens the Job Order (Sales staff or a Coordinator) after
discussion with the Support department -- not derived from priority or
any fixed SLA window. It is optional; a Job Order with no due date set
is simply not counted as due/overdue anywhere.

Status model reworked 2026-09-11: there is no manual "Resolved" step
any more. A Job Order auto-closes when its most recently submitted
Service Record is both Approved and marked Completed ('C', not
Uncompleted 'U') -- see app/services/service_records.py
maybe_auto_close_job_order(). CLOSED replaced the old manual
Resolve->Close two-step; VOID is new, a manual dead-end for a Job Order
that should never have been raised (duplicate, raised in error),
separate from a normal completed job.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobOrderStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    VOID = "void"


class JobOrderPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class JobOrder(Base):
    __tablename__ = "job_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Multi-company: every company-owned record carries its company, so
    # queries filter on it directly instead of joining out through the
    # customer -- and can never accidentally return another entity's data.
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_individuals.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )

    # System-generated running number (confirmed 2026-09-11 -- "all main
    # documents need to have a system generated running number to be
    # controlled"), same JO-<year>-<seq> pattern as every other document.
    job_order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[JobOrderPriority] = mapped_column(
        Enum(JobOrderPriority, name="job_order_priority"), default=JobOrderPriority.NORMAL
    )
    status: Mapped[JobOrderStatus] = mapped_column(
        Enum(JobOrderStatus, name="job_order_status"), default=JobOrderStatus.OPEN
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Manual, optional -- see module docstring. Drives Overdue/Due-Soon
    # monitoring once set; a null due_date is simply not counted.
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # "Option to also tick Job Order as Urgent then Rates will X1.5"
    # (confirmed 2026-09-11) -- a manual flag, not inferred from
    # priority. Used as a suggested (not enforced) minute-deduction
    # multiplier on Service Record approval -- see
    # app/services/service_records.py.
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Set only when status is VOID -- why this Job Order was voided
    # instead of worked (duplicate, raised in error, etc.). Required by
    # the void endpoint; the audit log also records who/when.
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Was resolved_at (a distinct "Resolved" step existed briefly);
    # renamed 2026-09-11 when that step was folded into auto-close --
    # this now simply records when CLOSED was reached.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["CompanyIndividual"] = relationship()  # noqa: F821
    contract: Mapped["Contract | None"] = relationship()  # noqa: F821
