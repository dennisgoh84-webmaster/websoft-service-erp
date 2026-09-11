"""
Pydantic request/response schemas for the Service Operations core API.

Hours are exposed to the API/UI as hours (float); the DB stores minutes
internally (see app/models/contracts.py) to keep SRV-007 rounding exact.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.accounting import AccountType, JournalStatus, VoucherType
from app.models.catalog import ProductType
from app.models.payables import BillMatchStatus, BillStatus, PurchaseOrderStatus
from app.models.contracts import ContractKind, ContractStatus, ExcessTreatment
from app.models.customers import CustomerType
from app.models.quotations import QuotationStatus
from app.models.core import UserRole
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrderPriority, JobOrderStatus
from app.models.licensing import LicenseType
from app.models.service_records import ServiceRecordOutcome, ServiceRecordStatus
from app.models.setup import SetupListType
from app.models.periods import PeriodStatus


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
    # Shown on printed forms' letterhead (Company Dashboard/Setup).
    phone: str | None
    website: str | None
    uen: str | None
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
    phone: str | None = None
    website: str | None = None
    uen: str | None = None
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


# ---- Customer Groups (tag linking separate companies in one group) --
class CustomerGroupCreate(BaseModel):
    name: str
    description: str | None = None


class CustomerGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CustomerGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


# ---- Customers ----
class CustomerCreate(BaseModel):
    customer_type: CustomerType = CustomerType.company
    name: str
    customer_group_id: uuid.UUID | None = None
    legacy_customer_code: str | None = None
    contact_person: str | None = None
    uen: str | None = None
    gst_registration_no: str | None = None
    billing_email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    address_country: str | None = None
    tags: str | None = None
    exclude_auto_sent: bool = False
    terms_and_conditions: str | None = None
    memo: str | None = None
    billing_notes: str | None = None
    # Days from invoice date. Terms vary per customer (confirmed
    # 2026-09-10); null means not yet agreed, and invoices carry no due
    # date until they are.
    payment_terms_days: int | None = Field(default=None, ge=0)


class CustomerUpdate(BaseModel):
    customer_type: CustomerType | None = None
    name: str | None = None
    customer_group_id: uuid.UUID | None = None
    legacy_customer_code: str | None = None
    contact_person: str | None = None
    uen: str | None = None
    gst_registration_no: str | None = None
    billing_email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    address_country: str | None = None
    tags: str | None = None
    exclude_auto_sent: bool | None = None
    terms_and_conditions: str | None = None
    memo: str | None = None
    billing_notes: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_type: CustomerType
    name: str
    customer_group_id: uuid.UUID | None
    legacy_customer_code: str | None
    contact_person: str | None
    uen: str | None
    gst_registration_no: str | None
    billing_email: str | None
    phone: str | None
    mobile: str | None
    website: str | None
    address_line1: str | None
    address_line2: str | None
    address_city: str | None
    address_state: str | None
    address_postal_code: str | None
    address_country: str | None
    tags: str | None
    exclude_auto_sent: bool
    terms_and_conditions: str | None
    memo: str | None
    billing_notes: str | None
    payment_terms_days: int | None
    is_active: bool
    created_at: datetime


class ContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    direct_line: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    direct_line: str | None = None


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    direct_line: str | None
    is_active: bool


class BranchCreate(BaseModel):
    branch_name: str
    branch_code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    address_country: str | None = None
    phone: str | None = None


class BranchUpdate(BaseModel):
    branch_name: str | None = None
    branch_code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    address_country: str | None = None
    phone: str | None = None


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    branch_name: str
    branch_code: str | None
    address_line1: str | None
    address_line2: str | None
    address_city: str | None
    address_state: str | None
    address_postal_code: str | None
    address_country: str | None
    phone: str | None
    is_active: bool


# ---- Contracts ----
class ContractCreate(BaseModel):
    customer_id: uuid.UUID
    contract_kind: ContractKind = ContractKind.SERVICE_SUPPORT
    # Must be >= 10 per SRV-002/SRV-012 for a SERVICE_SUPPORT contract;
    # ignored (forced to 0) for an ANNUAL contract, which has no hours.
    contracted_hours: float = Field(default=0, ge=0)
    contract_value_sgd: float = Field(gt=0)
    start_date: date


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    status: ContractStatus
    contract_kind: ContractKind
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
            contract_kind=contract.contract_kind,
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
    # Manual, optional -- set by Sales/Coordinator after discussion with
    # Support. Confirmed 2026-09-10: not derived from priority.
    due_date: date | None = None


class JobOrderAssign(BaseModel):
    assigned_to_user_id: uuid.UUID


class JobOrderSetDueDate(BaseModel):
    due_date: date | None = None


class JobOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None
    subject: str
    priority: JobOrderPriority
    status: JobOrderStatus
    assigned_to_user_id: uuid.UUID | None
    due_date: date | None
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
    voucher_number: str
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
            voucher_number=payment.voucher_number,
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


# ---- Chart of Accounts ----
class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    description: str | None
    is_active: bool


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1)
    account_type: AccountType
    description: str | None = None


class AccountUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    account_type: AccountType | None = None
    description: str | None = None
    is_active: bool | None = None


# ---- General Ledger / vouchers ----
class JournalLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    account_code: str | None = None
    account_name: str | None = None
    debit_sgd: float
    credit_sgd: float
    description: str | None


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    voucher_number: str
    voucher_type: VoucherType
    entry_date: date
    narration: str
    status: JournalStatus
    total_debit: float
    total_credit: float
    is_balanced: bool
    reverses_entry_id: uuid.UUID | None
    lines: list[JournalLineOut] = []

    @classmethod
    def from_model(cls, entry) -> "JournalEntryOut":
        return cls(
            id=entry.id,
            voucher_number=entry.voucher_number,
            voucher_type=entry.voucher_type,
            entry_date=entry.entry_date,
            narration=entry.narration,
            status=entry.status,
            total_debit=float(entry.total_debit),
            total_credit=float(entry.total_credit),
            is_balanced=entry.is_balanced,
            reverses_entry_id=entry.reverses_entry_id,
            lines=[
                JournalLineOut(
                    id=l.id,
                    account_id=l.account_id,
                    account_code=l.account.code if l.account else None,
                    account_name=l.account.name if l.account else None,
                    debit_sgd=float(l.debit_sgd),
                    credit_sgd=float(l.credit_sgd),
                    description=l.description,
                )
                for l in entry.lines
            ],
        )


class JournalLineCreate(BaseModel):
    account_id: uuid.UUID
    debit_sgd: float = Field(default=0, ge=0)
    credit_sgd: float = Field(default=0, ge=0)
    description: str | None = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    narration: str = Field(min_length=1)
    lines: list[JournalLineCreate]
    # Post immediately rather than leaving it as a draft.
    post: bool = False


class ReverseRequest(BaseModel):
    reason: str = Field(min_length=1)


class TrialBalanceRow(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    debit_sgd: float
    credit_sgd: float
    balance_sgd: float


class TrialBalance(BaseModel):
    as_at: date | None
    rows: list[TrialBalanceRow]
    total_debit: float
    total_credit: float
    is_balanced: bool


# ---- Accounts Payable ----
class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str | None
    address: str | None
    gst_registration_no: str | None
    payment_terms_days: int | None
    is_active: bool


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str | None = None
    address: str | None = None
    gst_registration_no: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)


class SupplierUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    address: str | None = None
    gst_registration_no: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    po_number: str
    supplier_id: uuid.UUID
    order_date: date
    description: str
    amount_sgd: float
    gst_amount_sgd: float
    total_amount_sgd: float
    status: PurchaseOrderStatus


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    order_date: date
    description: str = Field(min_length=1)
    amount_sgd: float = Field(gt=0)


class SupplierInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bill_number: str
    supplier_invoice_no: str | None
    supplier_id: uuid.UUID
    purchase_order_id: uuid.UUID | None
    invoice_date: date
    due_date: date | None
    description: str
    amount_sgd: float
    gst_amount_sgd: float
    total_amount_sgd: float
    amount_paid_sgd: float
    outstanding_sgd: float
    match_status: BillMatchStatus
    match_note: str | None
    status: BillStatus


class SupplierInvoiceCreate(BaseModel):
    supplier_id: uuid.UUID
    purchase_order_id: uuid.UUID | None = None
    supplier_invoice_no: str | None = None
    invoice_date: date
    description: str = Field(min_length=1)
    amount_sgd: float = Field(gt=0)
    gst_amount_sgd: float = Field(default=0, ge=0)


class SupplierPaymentAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_invoice_id: uuid.UUID
    bill_number: str | None = None
    amount_sgd: float


class SupplierPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    voucher_number: str
    supplier_id: uuid.UUID
    payment_date: date
    amount_sgd: float
    allocated_sgd: float
    unallocated_sgd: float
    method: str
    reference: str | None
    allocations: list[SupplierPaymentAllocationOut] = []

    @classmethod
    def from_model(cls, payment, bill_numbers: dict | None = None) -> "SupplierPaymentOut":
        numbers = bill_numbers or {}
        return cls(
            id=payment.id,
            voucher_number=payment.voucher_number,
            supplier_id=payment.supplier_id,
            payment_date=payment.payment_date,
            amount_sgd=float(payment.amount_sgd),
            allocated_sgd=float(payment.allocated_sgd),
            unallocated_sgd=float(payment.unallocated_sgd),
            method=payment.method,
            reference=payment.reference,
            allocations=[
                SupplierPaymentAllocationOut(
                    id=a.id,
                    supplier_invoice_id=a.supplier_invoice_id,
                    bill_number=numbers.get(a.supplier_invoice_id),
                    amount_sgd=float(a.amount_sgd),
                )
                for a in payment.allocations
            ],
        )


class SupplierPaymentAllocationEntry(BaseModel):
    supplier_invoice_id: uuid.UUID
    amount_sgd: float = Field(gt=0)


class SupplierPaymentCreate(BaseModel):
    supplier_id: uuid.UUID
    payment_date: date
    amount_sgd: float = Field(gt=0)
    method: str = "bank_transfer"
    reference: str | None = None
    notes: str | None = None
    allocations: list[SupplierPaymentAllocationEntry] = []


class SupplierAllocateRequest(BaseModel):
    allocations: list[SupplierPaymentAllocationEntry]


class APAgingRow(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    current: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    over_90: float
    total: float


class APAgingReport(BaseModel):
    as_at: date
    rows: list[APAgingRow]
    total: float


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
    # Financial summary -- same figures as the AR/AP aging reports and the
    # GL trial balance, just totalled for an at-a-glance dashboard tile
    # (see app/services/reports.py, which both this and the Accounting
    # Reports screen read from).
    ar_outstanding_sgd: float
    ar_overdue_sgd: float  # outstanding minus the "current" (not yet due) bucket
    ap_outstanding_sgd: float
    ap_overdue_sgd: float
    gl_is_balanced: bool


# ---- Product / Service Catalog ----
class ProductCreate(BaseModel):
    product_type: ProductType = ProductType.service
    name: str
    internal_reference: str | None = None
    product_category: str | None = None
    tags: str | None = None
    sales_price_sgd: float = Field(default=0, ge=0)
    cost_sgd: float | None = Field(default=None, ge=0)
    unit_of_measure: str | None = None
    tax_code: str = "SR"


class ProductUpdate(BaseModel):
    product_type: ProductType | None = None
    name: str | None = None
    internal_reference: str | None = None
    product_category: str | None = None
    tags: str | None = None
    sales_price_sgd: float | None = Field(default=None, ge=0)
    cost_sgd: float | None = Field(default=None, ge=0)
    unit_of_measure: str | None = None
    tax_code: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_type: ProductType
    name: str
    internal_reference: str | None
    product_category: str | None
    tags: str | None
    sales_price_sgd: float
    cost_sgd: float | None
    unit_of_measure: str | None
    tax_code: str
    is_active: bool
    created_at: datetime


# ---- Sales Quotation ----
class QuotationLineCreate(BaseModel):
    product_id: uuid.UUID | None = None
    description: str
    unit_of_measure: str | None = None
    quantity: float = Field(gt=0)
    unit_price_sgd: float = Field(ge=0)


class QuotationLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID | None
    description: str
    unit_of_measure: str | None
    quantity: float
    unit_price_sgd: float
    line_total_sgd: float


class QuotationCreate(BaseModel):
    customer_id: uuid.UUID
    quotation_date: date
    valid_until: date | None = None
    notes: str | None = None
    lines: list[QuotationLineCreate] = Field(default_factory=list)


class QuotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    quotation_number: str
    customer_id: uuid.UUID
    quotation_date: date
    valid_until: date | None
    status: QuotationStatus
    notes: str | None
    amount_sgd: float
    tax_code: str
    gst_rate: float
    gst_amount_sgd: float
    total_amount_sgd: float
    converted_contract_id: uuid.UUID | None
    converted_annual_contract_id: uuid.UUID | None
    created_at: datetime
    lines: list[QuotationLineOut]


class QuotationActionResult(BaseModel):
    quotation: QuotationOut
    message: str


# ---- Support Monitoring ----
class StaffMonitoringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    full_name: str
    open_job_orders: int
    overdue_job_orders: int
    due_soon_job_orders: int
    pending_service_records: int
    untested_software_tasks: int
    cm_svc_records_month: int
    cm_svc_records_today: int
    cm_svc_hours_month: float
    cm_svc_hours_today: float
    avg_daily_contract_hours: float


class MonitoringSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_job_orders: int
    total_open_job_orders: int
    total_overdue_job_orders: int
    unassigned_job_orders: int
    total_pending_service_records: int
    total_untested_software_tasks: int


class SupportMonitoringOut(BaseModel):
    as_at: date
    summary: MonitoringSummaryOut
    staff: list[StaffMonitoringOut]
    unassigned: StaffMonitoringOut


# ---- Software Task ----
class SoftwareTaskCreate(BaseModel):
    title: str
    description: str | None = None
    modules_affected: str | None = None
    assigned_programmer_id: uuid.UUID | None = None
    programming_finish_date: date | None = None
    programming_hours: float | None = Field(default=None, ge=0)
    tester_user_id: uuid.UUID | None = None


class SoftwareTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    modules_affected: str | None = None
    assigned_programmer_id: uuid.UUID | None = None
    programming_finish_date: date | None = None
    programming_hours: float | None = Field(default=None, ge=0)
    tester_user_id: uuid.UUID | None = None


class SoftwareTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    modules_affected: str | None
    assigned_programmer_id: uuid.UUID | None
    programming_finish_date: date | None
    programming_hours: float | None
    tester_user_id: uuid.UUID | None
    is_tested: bool
    tested_at: datetime | None
    created_at: datetime


# ---- Setup Lists (Nationality / Country / State / Area Code / Currency) ----
class SetupListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    list_type: SetupListType
    code: str
    name: str
    parent_code: str | None
    sort_order: int
    is_active: bool


class SetupListItemCreate(BaseModel):
    list_type: SetupListType
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=150)
    parent_code: str | None = None
    sort_order: int = 0


class SetupListItemUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    parent_code: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


# ---- GL Types ----
class GLTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    is_active: bool


class GLTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    account_type: AccountType


class GLTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    account_type: AccountType | None = None
    is_active: bool | None = None


# ---- Currency Rate Table ----
class CurrencyRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    currency_code: str
    rate_to_base: float
    effective_date: date
    is_active: bool


class CurrencyRateCreate(BaseModel):
    currency_code: str = Field(min_length=3, max_length=3)
    rate_to_base: float = Field(gt=0)
    effective_date: date


class CurrencyRateUpdate(BaseModel):
    rate_to_base: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


# ---- Bank Master File ----
class BankAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bank_name: str
    account_name: str
    account_number: str
    branch: str | None
    swift_code: str | None
    currency_code: str
    gl_account_id: uuid.UUID | None
    is_active: bool


class BankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=150)
    account_name: str = Field(min_length=1, max_length=150)
    account_number: str = Field(min_length=1, max_length=50)
    branch: str | None = None
    swift_code: str | None = None
    currency_code: str = Field(default="SGD", min_length=3, max_length=3)
    gl_account_id: uuid.UUID | None = None


class BankAccountUpdate(BaseModel):
    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    branch: str | None = None
    swift_code: str | None = None
    currency_code: str | None = None
    gl_account_id: uuid.UUID | None = None
    is_active: bool | None = None


# ---- Tax Type (TaxCode maintenance) ----
class TaxCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    rate_percent: float
    is_active: bool


class TaxCodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=100)
    rate_percent: float = Field(ge=0, le=100)


class TaxCodeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    rate_percent: float | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


# ---- Document Control ----
class DocumentSequenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    doc_kind: str
    prefix: str
    year: int
    last_number: int


class DocumentSequenceUpdate(BaseModel):
    last_number: int = Field(ge=0)
    reason: str = Field(min_length=1)


# ---- Accounting Periods / Year-End Closing ----
class AccountingPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    fiscal_year: int
    name: str
    period_start: date
    period_end: date
    status: PeriodStatus
    closed_at: datetime | None


class AccountingPeriodCreate(BaseModel):
    fiscal_year: int
    name: str = Field(min_length=1, max_length=50)
    period_start: date
    period_end: date


class FiscalYearClosureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    fiscal_year: int
    retained_earnings_account_id: uuid.UUID
    closing_journal_entry_id: uuid.UUID
    closed_at: datetime


class YearEndClosingRequest(BaseModel):
    fiscal_year: int
    retained_earnings_account_id: uuid.UUID


# ---- GST Return (read-only, doesn't file or post anything) ----
class GSTReturnRow(BaseModel):
    tax_code: str
    net_sgd: float
    tax_sgd: float
    document_count: int


class GSTReturn(BaseModel):
    period_start: date
    period_end: date
    output_rows: list[GSTReturnRow]  # sales -- output tax collected
    input_rows: list[GSTReturnRow]  # purchases -- input tax paid
    total_output_tax_sgd: float
    total_input_tax_sgd: float
    net_gst_payable_sgd: float  # output - input; negative means reclaimable
