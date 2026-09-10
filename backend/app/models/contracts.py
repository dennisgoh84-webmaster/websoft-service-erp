"""
Service Contracts models, implementing the confirmed SRV-001..018 rules
from docs/business-requirements.md.

Schema notes:
- Contract.contracted_hours / consumed_hours are stored in MINUTES
  internally (Numeric) to avoid float rounding issues with the 15-minute
  rounding rule (SRV-007); API/UI layers convert to hours for display.
- Contract.consumed_minutes is maintained by the service layer
  (app/services/contracts.py), not recomputed ad hoc, so the "never
  negative" invariant (SRV-004) has one place it's enforced.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

MINIMUM_CONTRACTED_HOURS = 10  # SRV-002 / SRV-012: hard minimum, no override
STANDARD_CONTRACT_MONTHS = 12  # SRV-001
HOUR_ROUNDING_MINUTES = 15  # SRV-007
RENEWAL_BACKDATING_WINDOW_DAYS = 14  # SRV-016 (2 weeks)
PRE_EXPIRY_CHECK_LEAD_DAYS = 30  # SRV-014
SERVICE_RECORD_SUBMISSION_DEADLINE_DAYS = 3  # SRV-015: Service Record submission deadline (business days, treated as calendar days for this demo)


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXCEEDED = "exceeded"  # hours fully consumed, still within term (SRV-001)
    EXPIRED = "expired"
    RENEWED = "renewed"


class ExcessTreatment(str, enum.Enum):
    BILLABLE = "billable"  # SRV-008: contract's blended rate, no pre-approval
    APPROVED_NON_BILLABLE = "approved_non_billable"
    WARRANTY_GOODWILL = "warranty_goodwill"  # SRV-013
    INTERNAL_WRITE_OFF = "internal_write_off"  # SRV-013
    OTHER = "other"


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            f"contracted_minutes >= {MINIMUM_CONTRACTED_HOURS * 60}",
            name="ck_contract_minimum_hours",
        ),
        CheckConstraint("consumed_minutes >= 0", name="ck_contract_consumed_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"), default=ContractStatus.DRAFT
    )

    # SRV-002/SRV-012: minimum 10 contracted hours, no override.
    contracted_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Maintained by app/services/contracts.py; never negative (SRV-004).
    consumed_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # BILL-001 (annual upfront) / SRV-008 (blended rate = value / hours).
    contract_value_sgd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)  # SRV-001: 12 months from start_date

    # SRV-010: renewal creates a NEW record referencing the prior one.
    renewed_from_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship()  # noqa: F821
    excess_usage_records: Mapped[list["ExcessUsageRecord"]] = relationship(
        back_populates="contract"
    )

    @property
    def remaining_minutes(self) -> int:
        return max(self.contracted_minutes - self.consumed_minutes, 0)


class ExcessUsageRecord(Base):
    """SRV-003/SRV-004: usage beyond contracted hours. Never auto-billed
    or auto-absorbed -- requires a reviewer decision (Nico, or Cherish as
    backup per SRV-011), with the decision and reason auditable."""

    __tablename__ = "excess_usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Multi-company: inherited from the contract it was raised against.
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    service_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_records.id"), nullable=False
    )
    excess_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    treatment: Mapped[ExcessTreatment | None] = mapped_column(
        Enum(ExcessTreatment, name="excess_treatment"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invoiced: Mapped[bool] = mapped_column(default=False)  # SRV-006: nothing left permanently unbilled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contract: Mapped["Contract"] = relationship(back_populates="excess_usage_records")

    @property
    def is_decided(self) -> bool:
        return self.treatment is not None


class ExpiredHoursRecord(Base):
    """SRV-005: unused hours forfeited at expiry, kept visible for
    reporting/audit -- never deleted, never converted to credit."""

    __tablename__ = "expired_hours_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    expired_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
