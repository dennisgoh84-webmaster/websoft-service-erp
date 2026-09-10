import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.billing import Invoice
from app.models.core import User
from app.schemas.schemas import InvoiceOut

router = APIRouter(prefix="/api/invoices", tags=["billing"])


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if contract_id:
        query = query.filter(Invoice.contract_id == contract_id)
    return query.order_by(Invoice.issued_at.desc()).all()
