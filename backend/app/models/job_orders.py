"""Job Orders (formerly "Helpdesk Tickets") -- Service Operations models.

SLA targets are explicitly deferred (SRV-009) -- priority is tracked but
no response/resolution time targets are enforced.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobOrderStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CLOSED = "closed"


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
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )
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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship()  # noqa: F821
    contract: Mapped["Contract | None"] = relationship()  # noqa: F821
