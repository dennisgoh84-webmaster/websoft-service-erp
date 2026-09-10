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


# ---- Customers ----
class CustomerCreate(BaseModel):
    name: str
    billing_email: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    billing_email: str | None
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
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None
    invoice_type: str
    description: str
    amount_sgd: float
    issued_at: datetime


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
