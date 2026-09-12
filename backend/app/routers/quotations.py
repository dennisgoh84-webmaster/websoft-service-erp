"""Sales Quotation API -- see app/models/quotations.py for the document
shape and app/services/quotations.py for totals + the accept -> auto-
Contract conversion (and its one open business decision)."""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.core import Company, User
from app.models.company_individuals import CompanyIndividual
from app.models.groups import AccessLevel
from app.models.quotations import Quotation, QuotationLine, QuotationStatus
from app.schemas.schemas import QuotationActionResult, QuotationCreate, QuotationOut
from app.services import audit, docx_forms, document_email, exports
from app.services import quotations as quotation_svc
from app.services.authority import require_module_access
from app.services.numbering import next_document_number

router = APIRouter(prefix="/api/quotations", tags=["quotations"])
MODULE = "sales"

QUOTATION_EXPORT_FIELDS = [
    "quotation_number", "customer_name", "quotation_date", "valid_until", "status",
    "amount_sgd", "gst_amount_sgd", "total_amount_sgd",
]


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


def _filter_quotations(
    db: Session, company_id: uuid.UUID, customer_id: uuid.UUID | None, status: QuotationStatus | None
) -> list[Quotation]:
    query = (
        db.query(Quotation)
        .options(selectinload(Quotation.lines))
        .filter(Quotation.company_id == company_id)
    )
    if customer_id:
        query = query.filter(Quotation.customer_id == customer_id)
    if status:
        query = query.filter(Quotation.status == status)
    return query.order_by(Quotation.quotation_date.desc(), Quotation.quotation_number.desc()).all()


@router.get("", response_model=list[QuotationOut])
def list_quotations(
    customer_id: uuid.UUID | None = None,
    status: QuotationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_quotations(db, current_user.company_id, customer_id, status)


def _quotation_row(q: Quotation, customer_name: str) -> dict:
    return {
        "quotation_number": q.quotation_number,
        "customer_name": customer_name,
        "quotation_date": q.quotation_date.isoformat(),
        "valid_until": q.valid_until.isoformat() if q.valid_until else "",
        "status": q.status.value,
        "amount_sgd": f"{float(q.amount_sgd):.2f}",
        "gst_amount_sgd": f"{float(q.gst_amount_sgd):.2f}",
        "total_amount_sgd": f"{float(q.total_amount_sgd):.2f}",
    }


def _quotations_for_export(
    db: Session, company_id: uuid.UUID, customer_id: uuid.UUID | None, status: QuotationStatus | None
) -> list[dict]:
    quotations = _filter_quotations(db, company_id, customer_id, status)
    customer_names = {c.id: c.name for c in db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)}
    return [_quotation_row(q, customer_names.get(q.customer_id, "")) for q in quotations]


@router.get("/export.csv")
def export_quotations_csv(
    customer_id: uuid.UUID | None = None,
    status: QuotationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _quotations_for_export(db, current_user.company_id, customer_id, status)
    csv_text = exports.rows_to_csv(QUOTATION_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quotations.csv"},
    )


@router.get("/export.xlsx")
def export_quotations_excel(
    customer_id: uuid.UUID | None = None,
    status: QuotationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _quotations_for_export(db, current_user.company_id, customer_id, status)
    data = exports.rows_to_excel(QUOTATION_EXPORT_FIELDS, rows, sheet_name="Quotations")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quotations.xlsx"},
    )


@router.get("/{quotation_id}", response_model=QuotationOut)
def get_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _quotation_or_404(db, quotation_id, current_user.company_id)


@router.get("/{quotation_id}/export.docx")
def export_quotation_docx(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    quotation = _quotation_or_404(db, quotation_id, current_user.company_id)
    customer = db.get(CompanyIndividual, quotation.customer_id)
    company = db.get(Company, current_user.company_id)
    data = docx_forms.quotation_to_docx(quotation, customer, company)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={quotation.quotation_number}.docx"},
    )


@router.post("/{quotation_id}/email")
def email_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Email Sales Quotation (2026-09-12) -- same real-send pattern as
    Purchase Order's Email button."""
    quotation = _quotation_or_404(db, quotation_id, current_user.company_id)
    customer = db.get(CompanyIndividual, quotation.customer_id)
    if not customer or not customer.billing_email:
        raise HTTPException(
            status_code=422,
            detail="This customer has no email on file -- add one on the Company/Individual page first.",
        )
    company = db.get(Company, current_user.company_id)
    docx_bytes = docx_forms.quotation_to_docx(quotation, customer, company)
    body = (
        f"Dear {customer.name},\n\n"
        f"Please find attached Quotation {quotation.quotation_number} dated "
        f"{quotation.quotation_date.isoformat()} for SGD {float(quotation.total_amount_sgd):.2f}.\n\n"
        f"Regards,\n{company.name if company else ''}"
    )
    try:
        document_email.send_document_email(
            to_email=customer.billing_email,
            subject=f"Quotation {quotation.quotation_number} - {company.name if company else ''}",
            body_text=body,
            docx_bytes=docx_bytes,
            filename_stem=quotation.quotation_number,
        )
    except document_email.DocumentEmailError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    audit.record(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        action="emailed",
        actor_user_id=current_user.id,
        details=f"{quotation.quotation_number} emailed to {customer.billing_email}",
    )
    db.commit()
    return {"sent": True, "to": customer.billing_email}


@router.post("", response_model=QuotationOut)
def create_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = db.get(CompanyIndividual, payload.customer_id)
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Company / Individual not found")
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
