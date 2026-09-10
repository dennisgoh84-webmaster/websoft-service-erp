import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.contracts import Contract, ContractStatus, ExcessUsageRecord
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    ContractCreate,
    ContractOut,
    ContractRenewRequest,
    ExcessUsageOut,
)
from app.services import billing as billing_svc
from app.services import contracts as contract_svc
from app.services import exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/contracts", tags=["contracts"])
MODULE = "service_contracts"

CONTRACT_EXPORT_FIELDS = [
    "customer_name", "contract_kind", "status", "contracted_hours", "consumed_hours",
    "remaining_hours", "contract_value_sgd", "start_date", "end_date",
]


def _get_contract_or_404(db: Session, contract_id: uuid.UUID, company_id: uuid.UUID) -> Contract:
    contract = db.get(Contract, contract_id)
    # Multi-company: another company's contract is "not found" here.
    if not contract or contract.company_id != company_id:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("", response_model=ContractOut)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    try:
        contract = contract_svc.create_contract(
            db,
            company_id=current_user.company_id,
            customer_id=payload.customer_id,
            contract_kind=payload.contract_kind,
            contracted_hours=payload.contracted_hours,
            contract_value_sgd=payload.contract_value_sgd,
            start_date=payload.start_date,
            actor_user_id=current_user.id,
        )
    except contract_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(contract)
    return ContractOut.from_model(contract)


def _filter_contracts(
    db: Session, company_id: uuid.UUID, status: ContractStatus | None, customer_id: uuid.UUID | None
) -> list[Contract]:
    query = db.query(Contract).filter(Contract.company_id == company_id)
    if status:
        query = query.filter(Contract.status == status)
    if customer_id:
        query = query.filter(Contract.customer_id == customer_id)
    return query.all()


@router.get("", response_model=list[ContractOut])
def list_contracts(
    status: ContractStatus | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return [ContractOut.from_model(c) for c in _filter_contracts(db, current_user.company_id, status, customer_id)]


def _contract_row(contract: Contract, customer_name: str) -> dict:
    out = ContractOut.from_model(contract)
    return {
        "customer_name": customer_name,
        "contract_kind": out.contract_kind.value,
        "status": out.status.value,
        "contracted_hours": f"{out.contracted_hours:.2f}",
        "consumed_hours": f"{out.consumed_hours:.2f}",
        "remaining_hours": f"{out.remaining_hours:.2f}",
        "contract_value_sgd": f"{out.contract_value_sgd:.2f}",
        "start_date": out.start_date.isoformat(),
        "end_date": out.end_date.isoformat(),
    }


def _contracts_for_export(
    db: Session, company_id: uuid.UUID, status: ContractStatus | None, customer_id: uuid.UUID | None
) -> list[dict]:
    contracts = _filter_contracts(db, company_id, status, customer_id)
    customer_names = {c.id: c.name for c in db.query(Customer).filter(Customer.company_id == company_id)}
    return [_contract_row(c, customer_names.get(c.customer_id, "")) for c in contracts]


@router.get("/export.csv")
def export_contracts_csv(
    status: ContractStatus | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _contracts_for_export(db, current_user.company_id, status, customer_id)
    csv_text = exports.rows_to_csv(CONTRACT_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contracts.csv"},
    )


@router.get("/export.xlsx")
def export_contracts_excel(
    status: ContractStatus | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _contracts_for_export(db, current_user.company_id, status, customer_id)
    data = exports.rows_to_excel(CONTRACT_EXPORT_FIELDS, rows, sheet_name="Contracts")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=contracts.xlsx"},
    )


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return ContractOut.from_model(_get_contract_or_404(db, contract_id, current_user.company_id))


@router.post("/{contract_id}/activate", response_model=ContractOut)
def activate_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    contract = _get_contract_or_404(db, contract_id, current_user.company_id)
    try:
        contract_svc.activate_contract(db, contract, actor_user_id=current_user.id)
        # BILL-001/BILL-002/BILL-005: annual upfront invoice, issued directly, on activation.
        billing_svc.issue_contract_annual_invoice(db, contract, actor_user_id=current_user.id)
    except contract_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(contract)
    return ContractOut.from_model(contract)


@router.post("/{contract_id}/renew", response_model=ContractOut)
def renew_contract(
    contract_id: uuid.UUID,
    payload: ContractRenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    prior = _get_contract_or_404(db, contract_id, current_user.company_id)
    try:
        new_contract = contract_svc.renew_contract(
            db,
            prior,
            contracted_hours=payload.contracted_hours,
            contract_value_sgd=payload.contract_value_sgd,
            actor_user_id=current_user.id,
            force_start_date=payload.force_start_date,
        )
    except contract_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(new_contract)
    return ContractOut.from_model(new_contract)


@router.get("/{contract_id}/excess-usage", response_model=list[ExcessUsageOut])
def list_excess_usage(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    _get_contract_or_404(db, contract_id, current_user.company_id)
    records = (
        db.query(ExcessUsageRecord).filter(ExcessUsageRecord.contract_id == contract_id).all()
    )
    return [ExcessUsageOut.from_model(r) for r in records]
