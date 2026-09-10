import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.contracts import Contract, ExcessUsageRecord
from app.models.core import User
from app.schemas.schemas import ExcessUsageDecision, ExcessUsageOut, InvoiceOut
from app.services import excess_usage as excess_svc

router = APIRouter(prefix="/api/excess-usage", tags=["excess-usage"])


@router.get("", response_model=list[ExcessUsageOut])
def list_all_excess_usage(
    pending_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ExcessUsageRecord)
    if pending_only:
        query = query.filter(ExcessUsageRecord.treatment.is_(None))
    return [ExcessUsageOut.from_model(r) for r in query.all()]


@router.post("/{record_id}/decide", response_model=ExcessUsageOut)
def decide_excess_usage(
    record_id: uuid.UUID,
    payload: ExcessUsageDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.get(ExcessUsageRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Excess usage record not found")
    contract = db.get(Contract, record.contract_id)
    try:
        excess_svc.decide_excess_usage(
            db,
            record,
            contract,
            treatment=payload.treatment,
            reason=payload.reason,
            reviewer=current_user,
        )
    except excess_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(record)
    return ExcessUsageOut.from_model(record)
