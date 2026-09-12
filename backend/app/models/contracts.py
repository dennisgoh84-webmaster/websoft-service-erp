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
    UniqueConstraint,
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


class ContractKind(str, enum.Enum):
    """Confirmed 2026-09-10 (SERVICE_SUPPORT/ANNUAL) and 2026-09-11
    (AD_HOC): the Contract Type a customer is on decides its "offset
    method" -- how work logged against it is settled:

    - SERVICE_SUPPORT -> deduct hours. The original hours-based
      contract; SRV-002/012's 10-hour minimum applies, and hours
      deduct as Service Records are approved.
    - ANNUAL -> time coverage. A term-only contract (e.g. an annual
      software warranty/maintenance contract) with a value and a
      duration but NO hours at all -- the minimum-hours rule does not
      apply (see the conditional CheckConstraint below).
    - AD_HOC -> ad hoc rates. No pre-paid hours and no upfront value
      (confirmed 2026-09-11): work is billed as it happens, off the
      contract's own reference `hourly_rate_sgd`. Nothing is
      deducted, exceeded, or auto-invoiced -- billing stays a manual
      step, same as ANNUAL.

    Job Orders and Service Records can be logged against any kind
    (confirmed 2026-09-10) -- for ANNUAL and AD_HOC there is just
    nothing to deduct or exceed, since neither has an hour pool."""

    SERVICE_SUPPORT = "service_support"
    ANNUAL = "annual"
    AD_HOC = "ad_hoc"


class ExcessTreatment(str, enum.Enum):
    BILLABLE = "billable"  # SRV-008: contract's blended rate, no pre-approval
    APPROVED_NON_BILLABLE = "approved_non_billable"
    WARRANTY_GOODWILL = "warranty_goodwill"  # SRV-013
    INTERNAL_WRITE_OFF = "internal_write_off"  # SRV-013
    OTHER = "other"


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        # SRV-002/012's 10-hour minimum applies only to SERVICE_SUPPORT
        # contracts -- an ANNUAL (term-only) contract has no hours at
        # all, confirmed 2026-09-10.
        CheckConstraint(
            f"contract_kind <> 'SERVICE_SUPPORT' OR contracted_minutes >= {MINIMUM_CONTRACTED_HOURS * 60}",
            name="ck_contract_minimum_hours",
        ),
        CheckConstraint("consumed_minutes >= 0", name="ck_contract_consumed_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_individuals.id"), nullable=False)

    # System-generated running number (confirmed 2026-09-11: "all main
    # documents need to have a system generated running number to be
    # controlled") -- allocated by app/services/numbering.py, same
    # CON-<year>-<seq> pattern as every other document type.
    contract_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"), default=ContractStatus.DRAFT
    )
    contract_kind: Mapped[ContractKind] = mapped_column(
        Enum(ContractKind, name="contract_kind"), nullable=False, default=ContractKind.SERVICE_SUPPORT
    )

    # SRV-002/SRV-012: minimum 10 contracted hours, no override. Zero
    # for an ANNUAL contract (contract_kind), which has no hours.
    contracted_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Maintained by app/services/contracts.py; never negative (SRV-004).
    consumed_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # BILL-001 (annual upfront) / SRV-008 (blended rate = value / hours).
    # Zero for an AD_HOC contract (confirmed 2026-09-11), which has no
    # upfront value -- work is billed as it happens.
    contract_value_sgd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # AD_HOC's reference rate (confirmed 2026-09-11): a rate a manual
    # invoice can be based on. Never read by any automatic billing --
    # see the ContractKind docstring. Null for SERVICE_SUPPORT/ANNUAL.
    hourly_rate_sgd: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # The staff member who owns this contract commercially -- optional,
    # any user (not restricted to the sales_manager role, since a small
    # team may have more than one person selling).
    sales_staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)  # SRV-001: 12 months from start_date

    # SRV-010: renewal creates a NEW record referencing the prior one.
    renewed_from_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["CompanyIndividual"] = relationship()  # noqa: F821
    excess_usage_records: Mapped[list["ExcessUsageRecord"]] = relationship(
        back_populates="contract"
    )
    products: Mapped[list["ContractProduct"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
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


class LicenseDeploymentType(str, enum.Enum):
    """Deployment mode of a licensed software product covered by a
    contract (2026-09-12) -- LOCAL (installed on the customer's own
    machine), RDP (remote desktop/hosted access), WEB (browser-based).
    Named to avoid colliding with app.models.licensing.LicenseType,
    which is an unrelated concept (this system's own module-licensing
    tier: included/add-on/trial)."""

    LOCAL = "local"
    RDP = "rdp"
    WEB = "web"


class ContractProduct(Base):
    """Product coverage (confirmed 2026-09-11): which catalog items a
    contract actually covers, e.g. "Server maintenance" and "Network
    support" but not other services. A plain link -- it doesn't change
    how hours/value/rate work, it's what the contract is scoped to.

    license_type/number_of_licenses (2026-09-12) are optional, set only
    when the covered product is a licensed software item -- e.g. 5
    (RDP) licenses of a hosted accounting package. Left null for
    coverage that isn't a per-seat license at all (e.g. "Server
    maintenance")."""

    __tablename__ = "contract_products"
    __table_args__ = (UniqueConstraint("contract_id", "product_id", name="uq_contract_product"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    license_type: Mapped[LicenseDeploymentType | None] = mapped_column(
        Enum(LicenseDeploymentType, name="license_deployment_type"), nullable=True
    )
    number_of_licenses: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contract: Mapped["Contract"] = relationship(back_populates="products")
    product: Mapped["Product"] = relationship()  # noqa: F821
