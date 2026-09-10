import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.billing import Invoice
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import InvoiceOut
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/invoices", tags=["billing"])
MODULE = "billing"


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(Invoice).filter(Invoice.company_id == current_user.company_id)
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if contract_id:
        query = query.filter(Invoice.contract_id == contract_id)
    return query.order_by(Invoice.issued_at.desc()).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice or invoice.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
