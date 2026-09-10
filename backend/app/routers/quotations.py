"""Sales Quotation API -- see app/models/quotations.py for the document
shape and app/services/quotations.py for totals + the accept -> auto-
Contract conversion (and its one open business decision)."""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.models.quotations import Quotation, QuotationLine, QuotationStatus
from app.schemas.schemas import QuotationActionResult, QuotationCreate, QuotationOut
from app.services import audit
from app.services import quotations as quotation_svc
from app.services.authority import require_module_access
from app.services.numbering import next_document_number

router = APIRouter(prefix="/api/quotations", tags=["quotations"])
MODULE = "sales"


def _quotation_or_404(db: Session, quotation_id: uuid.UUID, company_id: uuid.UUID) -> Quotation:
    quotation = (
        db.query(Quotation)
        .options(selectinload(Quotation.lines))
        .filter(Quotation.id == quotation_id, Quotation.company_id == company_id)
        .first()
    )
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return quotation


@router.get("", response_model=list[QuotationOut])
def list_quotations(
    customer_id: uuid.UUID | None = None,
    status: QuotationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = (
        db.query(Quotation)
        .options(selectinload(Quotation.lines))
        .filter(Quotation.company_id == current_user.company_id)
    )
    if customer_id:
        query = query.filter(Quotation.customer_id == customer_id)
    if status:
        query = query.filter(Quotation.status == status)
    return query.order_by(Quotation.quotation_date.desc(), Quotation.quotation_number.desc()).all()


@router.get("/{quotation_id}", response_model=QuotationOut)
def get_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _quotation_or_404(db, quotation_id, current_user.company_id)


@router.post("", response_model=QuotationOut)
def create_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = db.get(Customer, payload.customer_id)
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not payload.lines:
        raise HTTPException(status_code=422, detail="A quotation needs at least one line.")

    quotation = Quotation(
        company_id=current_user.company_id,
        quotation_number=next_document_number(db, company_id=current_user.company_id, doc_kind="quotation"),
        customer_id=payload.customer_id,
        quotation_date=payload.quotation_date,
        valid_until=payload.valid_until,
        notes=payload.notes,
        created_by_user_id=current_user.id,
    )
    db.add(quotation)
    db.flush()

    for line in payload.lines:
        qty = Decimal(str(line.quantity))
        price = Decimal(str(line.unit_price_sgd))
        db.add(
            QuotationLine(
                quotation_id=quotation.id,
                product_id=line.product_id,
                description=line.description,
                unit_of_measure=line.unit_of_measure,
                quantity=qty,
                unit_price_sgd=price,
                line_total_sgd=(qty * price).quantize(Decimal("0.01")),
            )
        )
    db.flush()
    db.refresh(quotation)
    quotation_svc.recompute_totals(db, quotation)

    audit.record(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{quotation.quotation_number} for {customer.name}",
        new_value={"customer": customer.name, "total_amount_sgd": float(quotation.total_amount_sgd)},
    )
    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/{quotation_id}/send", response_model=QuotationOut)
def send_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    quotation = _quotation_or_404(db, quotation_id, current_user.company_id)
    if quotation.status != QuotationStatus.draft:
        raise HTTPException(status_code=409, detail="Only a draft quotation can be sent.")
    quotation.status = QuotationStatus.sent
    audit.record(
        db, entity_type="quotation", entity_id=quotation.id, action="sent", actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/{quotation_id}/accept", response_model=QuotationActionResult)
def accept_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    quotation = _quotation_or_404(db, quotation_id, current_user.company_id)
    if quotation.status not in (QuotationStatus.draft, QuotationStatus.sent):
        raise HTTPException(status_code=409, detail=f"Cannot accept a {quotation.status.value} quotation.")
    message = quotation_svc.accept_quotation(db, quotation, actor_user_id=current_user.id)
    db.commit()
    db.refresh(quotation)
    return QuotationActionResult(quotation=quotation, message=message)


@router.post("/{quotation_id}/reject", response_model=QuotationOut)
def reject_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    quotation = _quotation_or_404(db, quotation_id, current_user.company_id)
    if quotation.status not in (QuotationStatus.draft, QuotationStatus.sent):
        raise HTTPException(status_code=409, detail=f"Cannot reject a {quotation.status.value} quotation.")
    quotation.status = QuotationStatus.rejected
    audit.record(
        db, entity_type="quotation", entity_id=quotation.id, action="rejected", actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(quotation)
    return quotation
