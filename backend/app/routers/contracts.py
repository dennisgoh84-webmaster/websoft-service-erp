import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.contracts import Contract, ExcessUsageRecord
from app.models.core import User
from app.schemas.schemas import (
    ContractCreate,
    ContractOut,
    ContractRenewRequest,
    ExcessUsageOut,
)
from app.services import billing as billing_svc
from app.services import contracts as contract_svc

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _get_contract_or_404(db: Session, contract_id: uuid.UUID) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("", response_model=ContractOut)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        contract = contract_svc.create_contract(
            db,
            company_id=current_user.company_id,
            customer_id=payload.customer_id,
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


@router.get("", response_model=list[ContractOut])
def list_contracts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contracts = db.query(Contract).filter(Contract.company_id == current_user.company_id).all()
    return [ContractOut.from_model(c) for c in contracts]


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ContractOut.from_model(_get_contract_or_404(db, contract_id))


@router.post("/{contract_id}/activate", response_model=ContractOut)
def activate_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = _get_contract_or_404(db, contract_id)
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
    current_user: User = Depends(get_current_user),
):
    prior = _get_contract_or_404(db, contract_id)
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
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(ExcessUsageRecord).filter(ExcessUsageRecord.contract_id == contract_id).all()
    )
    return [ExcessUsageOut.from_model(r) for r in records]
