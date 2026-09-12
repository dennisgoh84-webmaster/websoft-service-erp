import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.contracts import Contract, ExcessUsageRecord
from app.models.core import User
from app.models.company_individuals import CompanyIndividual
from app.models.groups import AccessLevel
from app.schemas.schemas import ExcessUsageDecision, ExcessUsageOut, InvoiceOut
from app.services import exports
from app.services import excess_usage as excess_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/excess-usage", tags=["excess-usage"])
MODULE = "service_contracts"

EXCESS_USAGE_EXPORT_FIELDS = ["customer_name", "excess_hours", "treatment", "reason", "invoiced"]


def _filter_excess_usage(db: Session, company_id: uuid.UUID, pending_only: bool) -> list[ExcessUsageRecord]:
    query = db.query(ExcessUsageRecord).filter(ExcessUsageRecord.company_id == company_id)
    if pending_only:
        query = query.filter(ExcessUsageRecord.treatment.is_(None))
    return query.all()


@router.get("", response_model=list[ExcessUsageOut])
def list_all_excess_usage(
    pending_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return [ExcessUsageOut.from_model(r) for r in _filter_excess_usage(db, current_user.company_id, pending_only)]


def _excess_usage_for_export(db: Session, company_id: uuid.UUID, pending_only: bool) -> list[dict]:
    records = _filter_excess_usage(db, company_id, pending_only)
    contracts = {
        c.id: c.customer_id
        for c in db.query(Contract).filter(Contract.id.in_({r.contract_id for r in records}))
    } if records else {}
    customer_names = {c.id: c.name for c in db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)}
    rows = []
    for r in records:
        out = ExcessUsageOut.from_model(r)
        rows.append(
            {
                "customer_name": customer_names.get(contracts.get(r.contract_id), ""),
                "excess_hours": f"{out.excess_hours:.2f}",
                "treatment": out.treatment.value if out.treatment else "",
                "reason": out.reason or "",
                "invoiced": out.invoiced,
            }
        )
    return rows


@router.get("/export.csv")
def export_excess_usage_csv(
    pending_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _excess_usage_for_export(db, current_user.company_id, pending_only)
    csv_text = exports.rows_to_csv(EXCESS_USAGE_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=excess-usage.csv"},
    )


@router.get("/export.xlsx")
def export_excess_usage_excel(
    pending_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _excess_usage_for_export(db, current_user.company_id, pending_only)
    data = exports.rows_to_excel(EXCESS_USAGE_EXPORT_FIELDS, rows, sheet_name="Excess Usage")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=excess-usage.xlsx"},
    )


@router.post("/{record_id}/decide", response_model=ExcessUsageOut)
def decide_excess_usage(
    record_id: uuid.UUID,
    payload: ExcessUsageDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    record = db.get(ExcessUsageRecord, record_id)
    if not record or record.company_id != current_user.company_id:
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
