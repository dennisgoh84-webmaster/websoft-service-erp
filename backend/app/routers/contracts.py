import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.contracts import Contract, ContractKind, ContractProduct, ContractStatus, ExcessUsageRecord
from app.models.core import User
from app.models.company_individuals import CompanyIndividual
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    ContractCreate,
    ContractOut,
    ContractRenewRequest,
    ContractUpdate,
    ExcessUsageOut,
)
from app.services import audit
from app.services import billing as billing_svc
from app.services import contracts as contract_svc
from app.services import exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/contracts", tags=["contracts"])
MODULE = "service_contracts"

CONTRACT_EXPORT_FIELDS = [
    "contract_number", "customer_name", "contract_kind", "status", "contracted_hours",
    "consumed_hours", "remaining_hours", "contract_value_sgd", "hourly_rate_sgd", "sales_staff",
    "products", "start_date", "end_date",
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
            hourly_rate_sgd=payload.hourly_rate_sgd,
            sales_staff_id=payload.sales_staff_id,
            product_ids=payload.product_ids,
        )
    except contract_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(contract)
    return ContractOut.from_model(contract)


def _filter_contracts(
    db: Session,
    company_id: uuid.UUID,
    status: ContractStatus | None,
    customer_id: uuid.UUID | None,
    contract_kind: ContractKind | None = None,
    sales_staff_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
) -> list[Contract]:
    query = db.query(Contract).filter(Contract.company_id == company_id)
    if status:
        query = query.filter(Contract.status == status)
    if customer_id:
        query = query.filter(Contract.customer_id == customer_id)
    if contract_kind:
        query = query.filter(Contract.contract_kind == contract_kind)
    if sales_staff_id:
        query = query.filter(Contract.sales_staff_id == sales_staff_id)
    if product_id:
        query = query.join(ContractProduct).filter(ContractProduct.product_id == product_id)
    # Coverage-date range: any contract whose own start/end overlaps the
    # given window, same "overlap" semantics as Operations Reports'
    # Contracts report (app/services/reports.py).
    if coverage_start:
        query = query.filter(Contract.end_date >= coverage_start)
    if coverage_end:
        query = query.filter(Contract.start_date <= coverage_end)
    return query.order_by(Contract.end_date).all()


@router.get("", response_model=list[ContractOut])
def list_contracts(
    status: ContractStatus | None = None,
    customer_id: uuid.UUID | None = None,
    contract_kind: ContractKind | None = None,
    sales_staff_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    contracts = _filter_contracts(
        db, current_user.company_id, status, customer_id, contract_kind, sales_staff_id,
        product_id, coverage_start, coverage_end,
    )
    return [ContractOut.from_model(c) for c in contracts]


@router.patch("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: uuid.UUID,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Admin fields adjustable without a renewal -- sales staff owner
    and product coverage. Everything else about a contract (kind,
    hours, value, term) only changes via renewal (SRV-010)."""
    contract = _get_contract_or_404(db, contract_id, current_user.company_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}

    if "sales_staff_id" in fields:
        old_value["sales_staff_id"] = str(contract.sales_staff_id) if contract.sales_staff_id else None
        contract.sales_staff_id = fields["sales_staff_id"]
        new_value["sales_staff_id"] = str(contract.sales_staff_id) if contract.sales_staff_id else None

    if fields.get("product_ids") is not None:
        from app.models.catalog import Product

        old_value["product_ids"] = [str(cp.product_id) for cp in contract.products]
        for cp in list(contract.products):
            db.delete(cp)
        db.flush()
        for product_id in fields["product_ids"]:
            product = db.get(Product, product_id)
            if product is None or product.company_id != current_user.company_id:
                raise HTTPException(status_code=404, detail="Unknown product in product coverage")
            db.add(ContractProduct(contract_id=contract.id, product_id=product_id))
        new_value["product_ids"] = [str(p) for p in fields["product_ids"]]

    audit.record(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(contract)
    return ContractOut.from_model(contract)


def _contract_row(contract: Contract, customer_name: str, staff_name: str) -> dict:
    out = ContractOut.from_model(contract)
    return {
        "contract_number": out.contract_number,
        "customer_name": customer_name,
        "contract_kind": out.contract_kind.value,
        "status": out.status.value,
        "contracted_hours": f"{out.contracted_hours:.2f}",
        "consumed_hours": f"{out.consumed_hours:.2f}",
        "remaining_hours": f"{out.remaining_hours:.2f}",
        "contract_value_sgd": f"{out.contract_value_sgd:.2f}",
        "hourly_rate_sgd": f"{out.hourly_rate_sgd:.2f}" if out.hourly_rate_sgd is not None else "",
        "sales_staff": staff_name,
        "products": ", ".join(p.product_name for p in out.products),
        "start_date": out.start_date.isoformat(),
        "end_date": out.end_date.isoformat(),
    }


def _contracts_for_export(
    db: Session,
    company_id: uuid.UUID,
    status: ContractStatus | None,
    customer_id: uuid.UUID | None,
    contract_kind: ContractKind | None = None,
    sales_staff_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
) -> list[dict]:
    contracts = _filter_contracts(
        db, company_id, status, customer_id, contract_kind, sales_staff_id,
        product_id, coverage_start, coverage_end,
    )
    customer_names = {c.id: c.name for c in db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)}
    staff_names = {u.id: u.full_name for u in db.query(User).all()}
    return [
        _contract_row(c, customer_names.get(c.customer_id, ""), staff_names.get(c.sales_staff_id, ""))
        for c in contracts
    ]


@router.get("/export.csv")
def export_contracts_csv(
    status: ContractStatus | None = None,
    customer_id: uuid.UUID | None = None,
    contract_kind: ContractKind | None = None,
    sales_staff_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _contracts_for_export(
        db, current_user.company_id, status, customer_id, contract_kind, sales_staff_id,
        product_id, coverage_start, coverage_end,
    )
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
    contract_kind: ContractKind | None = None,
    sales_staff_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _contracts_for_export(
        db, current_user.company_id, status, customer_id, contract_kind, sales_staff_id,
        product_id, coverage_start, coverage_end,
    )
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
        # BILL-001/BILL-002/BILL-005: annual upfront invoice, issued directly,
        # on activation -- except AD_HOC (confirmed 2026-09-11), which has no
        # upfront value to invoice; billing happens manually as work is done.
        if contract.contract_kind != ContractKind.AD_HOC:
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
            hourly_rate_sgd=payload.hourly_rate_sgd,
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
