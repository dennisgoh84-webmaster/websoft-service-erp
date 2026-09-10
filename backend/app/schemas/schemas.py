"""
Pydantic request/response schemas for the Service Operations core API.

Hours are exposed to the API/UI as hours (float); the DB stores minutes
internally (see app/models/contracts.py) to keep SRV-007 rounding exact.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.contracts import ContractStatus, ExcessTreatment
from app.models.core import UserRole
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrderPriority, JobOrderStatus
from app.models.licensing import LicenseType
from app.models.service_records import ServiceRecordOutcome, ServiceRecordStatus


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    group_id: uuid.UUID | None = None
    # The company this user is currently working in (multi-company).
    company_id: uuid.UUID | None = None


# ---- Company Setup / multi-company ----
class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    country: str
    currency: str
    timezone: str
    logo: str | None
    # Shown on tax invoices.
    address: str | None
    gst_registration_no: str | None
    # Approval thresholds -- null means "always require owner approval",
    # since the values were never decided (open items 2.7 / 3.4 / 4.4).
    write_off_approval_threshold_sgd: float | None
    credit_note_approval_threshold_sgd: float | None
    po_approval_threshold_sgd: float | None
    is_active: bool
    created_at: datetime


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    country: str = "Singapore"
    currency: str = "SGD"
    timezone: str = "Asia/Singapore"
    logo: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    currency: str | None = None
    timezone: str | None = None
    # A data URI ("data:image/png;base64,..."). Pass null to clear the logo.
    logo: str | None = None
    address: str | None = None
    gst_registration_no: str | None = None
    write_off_approval_threshold_sgd: float | None = None
    credit_note_approval_threshold_sgd: float | None = None
    po_approval_threshold_sgd: float | None = None
    is_active: bool | None = None


# ---- Staff Master (Users) ----
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    group_id: uuid.UUID | None
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=8)
    role: UserRole
    group_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    group_id: uuid.UUID | None = None


class UserPasswordReset(BaseModel):
    new_password: str = Field(min_length=8)


class UserCompanyAccessOut(BaseModel):
    """One company a staff member may work in, and their Group there."""

    company_id: uuid.UUID
    company_name: str
    group_id: uuid.UUID | None
    group_name: str | None


class UserCompanyAccessEntry(BaseModel):
    company_id: uuid.UUID
    group_id: uuid.UUID | None = None


class UserCompanyAccessUpdate(BaseModel):
    """Replaces the full set of companies this staff member may work in
    (and their Group in each). Omitting a company revokes its access."""

    access: list[UserCompanyAccessEntry]


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    actor_name: str | None
    reason: str | None
    details: str | None
    old_value: str | None
    new_value: str | None
    ip_address: str | None
    user_agent: str | None
    device_id: str | None
    at: datetime


# ---- Group Authority ----
class GroupAuthorityOut(BaseModel):
    module_key: str
    access_level: AccessLevel


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    authorities: list[GroupAuthorityOut] = []
    member_count: int = 0

    @classmethod
    def from_model(cls, group, member_count: int = 0) -> "GroupOut":
        return cls(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            authorities=[
                GroupAuthorityOut(module_key=a.module_key, access_level=a.access_level)
                for a in group.authorities
            ],
            member_count=member_count,
        )


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupAuthoritySet(BaseModel):
    module_key: str
    access_level: AccessLevel


class GroupAuthoritiesUpdateRequest(BaseModel):
    authorities: list[GroupAuthoritySet]


# ---- Customers ----
class CustomerCreate(BaseModel):
    name: str
    billing_email: str | None = None
    billing_address: str | None = None
    # Days from invoice date. Terms vary per customer (confirmed
    # 2026-09-10); null means not yet agreed, and invoices carry no due
    # date until they are.
    payment_terms_days: int | None = Field(default=None, ge=0)


class CustomerUpdate(BaseModel):
    name: str | None = None
    billing_email: str | None = None
    billing_address: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    billing_email: str | None
    billing_address: str | None
    payment_terms_days: int | None
    is_active: bool


# ---- Contracts ----
class ContractCreate(BaseModel):
    customer_id: uuid.UUID
    contracted_hours: float = Field(ge=0, description="Must be >= 10 per SRV-002/SRV-012")
    contract_value_sgd: float = Field(gt=0)
    start_date: date


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    status: ContractStatus
    contracted_hours: float
    consumed_hours: float
    remaining_hours: float
    contract_value_sgd: float
    start_date: date
    end_date: date
    renewed_from_contract_id: uuid.UUID | None

    @classmethod
    def from_model(cls, contract) -> "ContractOut":
        return cls(
            id=contract.id,
            customer_id=contract.customer_id,
            status=contract.status,
            contracted_hours=contract.contracted_minutes / 60,
            consumed_hours=contract.consumed_minutes / 60,
            remaining_hours=contract.remaining_minutes / 60,
            contract_value_sgd=float(contract.contract_value_sgd),
            start_date=contract.start_date,
            end_date=contract.end_date,
            renewed_from_contract_id=contract.renewed_from_contract_id,
        )


class ContractRenewRequest(BaseModel):
    contracted_hours: float = Field(ge=0)
    contract_value_sgd: float = Field(gt=0)
    force_start_date: date | None = None


# ---- Job Orders (formerly "Tickets") ----
class JobOrderCreate(BaseModel):
    customer_id: uuid.UUID
    contract_id: uuid.UUID
    subject: str
    priority: JobOrderPriority = JobOrderPriority.NORMAL


class JobOrderAssign(BaseModel):
    assigned_to_user_id: uuid.UUID


class JobOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None
    subject: str
    priority: JobOrderPriority
    status: JobOrderStatus
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime


# ---- Service Records (formerly "Timesheets") ----
class ServiceRecordCreate(BaseModel):
    job_order_id: uuid.UUID
    employee_user_id: uuid.UUID
    work_date: date
    raw_minutes: int = Field(gt=0)


class ServiceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    job_order_id: uuid.UUID
    employee_user_id: uuid.UUID
    work_date: date
    raw_minutes: int
    rounded_minutes: int
    status: ServiceRecordStatus
    outcome: ServiceRecordOutcome
    is_late: bool


# ---- Excess usage ----
class ExcessUsageDecision(BaseModel):
    treatment: ExcessTreatment
    reason: str = Field(min_length=1)


class ExcessUsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contract_id: uuid.UUID
    service_record_id: uuid.UUID
    excess_hours: float
    treatment: ExcessTreatment | None
    reason: str | None
    decided_by_user_id: uuid.UUID | None
    invoiced: bool

    @classmethod
    def from_model(cls, record) -> "ExcessUsageOut":
        return cls(
            id=record.id,
            contract_id=record.contract_id,
            service_record_id=record.service_record_id,
            excess_hours=record.excess_minutes / 60,
            treatment=record.treatment,
            reason=record.reason,
            decided_by_user_id=record.decided_by_user_id,
            invoiced=record.invoiced,
        )


# ---- Billing ----
class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None
    invoice_type: str
    description: str
    # Net of GST -- this is the revenue figure. GST collected is a
    # liability owed to IRAS, not income.
    amount_sgd: float
    tax_code: str
    gst_rate: float
    gst_amount_sgd: float
    total_amount_sgd: float
    amount_paid_sgd: float
    outstanding_sgd: float
    due_date: date | None
    status: str
    is_disputed: bool
    dispute_note: str | None
    issued_at: datetime


# ---- Accounts Receivable ----
class PaymentAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str | None = None
    amount_sgd: float


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    payment_date: date
    amount_sgd: float
    allocated_sgd: float
    unallocated_sgd: float
    method: str
    reference: str | None
    notes: str | None
    allocations: list[PaymentAllocationOut] = []

    @classmethod
    def from_model(cls, payment, invoice_numbers: dict | None = None) -> "PaymentOut":
        numbers = invoice_numbers or {}
        return cls(
            id=payment.id,
            customer_id=payment.customer_id,
            payment_date=payment.payment_date,
            amount_sgd=float(payment.amount_sgd),
            allocated_sgd=float(payment.allocated_sgd),
            unallocated_sgd=float(payment.unallocated_sgd),
            method=payment.method.value,
            reference=payment.reference,
            notes=payment.notes,
            allocations=[
                PaymentAllocationOut(
                    id=a.id,
                    invoice_id=a.invoice_id,
                    invoice_number=numbers.get(a.invoice_id),
                    amount_sgd=float(a.amount_sgd),
                )
                for a in payment.allocations
            ],
        )


class PaymentAllocationEntry(BaseModel):
    invoice_id: uuid.UUID
    amount_sgd: float = Field(gt=0)


class PaymentCreate(BaseModel):
    customer_id: uuid.UUID
    payment_date: date
    amount_sgd: float = Field(gt=0)
    method: str = "bank_transfer"
    reference: str | None = None
    notes: str | None = None
    # AR-001: allocation is manual, so it is optional here -- a receipt
    # can be recorded first and allocated later.
    allocations: list[PaymentAllocationEntry] = []


class AllocateRequest(BaseModel):
    allocations: list[PaymentAllocationEntry]


class InvoiceWriteOffRequest(BaseModel):
    reason: str = Field(min_length=1)


class InvoiceDisputeRequest(BaseModel):
    # AR-003: flags the dispute for Finance; collections continue.
    is_disputed: bool
    note: str | None = None


class AgingRow(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    current: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    over_90: float
    total: float


class AgingReport(BaseModel):
    as_at: date
    rows: list[AgingRow]
    current: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    over_90: float
    total: float


class StatementLine(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    description: str
    issued_on: date
    due_date: date | None
    total_amount_sgd: float
    amount_paid_sgd: float
    outstanding_sgd: float
    status: str
    is_disputed: bool
    days_overdue: int


class CustomerStatement(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    as_at: date
    payment_terms_days: int | None
    lines: list[StatementLine]
    total_outstanding_sgd: float
    unallocated_credit_sgd: float


# ---- Module Control / licensing ----
class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    name: str
    description: str | None
    is_built: bool
    enabled: bool
    license_type: LicenseType


class ModuleToggleRequest(BaseModel):
    enabled: bool
    license_type: LicenseType | None = None
    notes: str | None = None


# ---- Dashboard ----
class DashboardSummary(BaseModel):
    active_contracts: int
    contracts_expiring_soon: int  # SRV-014: within 30 days of expiry
    total_contracted_hours: float
    total_consumed_hours: float
    total_remaining_hours: float
    excess_awaiting_review: int
    open_job_orders: int
    missing_service_records: int  # SRV-015: submitted more than 3 business days after the work date
    invoices_total_sgd: float
    invoices_count: int
