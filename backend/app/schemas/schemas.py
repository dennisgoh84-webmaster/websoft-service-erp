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
from app.models.tickets import TicketPriority, TicketStatus
from app.models.timesheets import TimesheetOutcome, TimesheetStatus


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


# ---- Tickets ----
class TicketCreate(BaseModel):
    customer_id: uuid.UUID
    contract_id: uuid.UUID
    subject: str
    priority: TicketPriority = TicketPriority.NORMAL


class TicketAssign(BaseModel):
    assigned_to_user_id: uuid.UUID


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    contract_id: uuid.UUID | None
    subject: str
    priority: TicketPriority
    status: TicketStatus
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime


# ---- Timesheets ----
class TimesheetCreate(BaseModel):
    ticket_id: uuid.UUID
    employee_user_id: uuid.UUID
    work_date: date
    raw_minutes: int = Field(gt=0)


class TimesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_id: uuid.UUID
    employee_user_id: uuid.UUID
    work_date: date
    raw_minutes: int
    rounded_minutes: int
    status: TimesheetStatus
    outcome: TimesheetOutcome
    is_late: bool


# ---- Excess usage ----
class ExcessUsageDecision(BaseModel):
    treatment: ExcessTreatment
    reason: str = Field(min_length=1)


class ExcessUsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contract_id: uuid.UUID
    timesheet_entry_id: uuid.UUID
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
            timesheet_entry_id=record.timesheet_entry_id,
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
