"""
Accounts Payable API -- suppliers, purchase orders, supplier invoices
(2-way matched per PUR-002) and Payment Vouchers.

See app/services/payables.py for the rules themselves.
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.payables import (
    BillStatus,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
    SupplierInvoice,
    SupplierPayment,
)
from app.schemas.schemas import (
    APAgingReport,
    APAgingRow,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    SupplierAllocateRequest,
    SupplierCreate,
    SupplierInvoiceCreate,
    SupplierInvoiceOut,
    SupplierOut,
    SupplierPaymentCreate,
    SupplierPaymentOut,
    SupplierUpdate,
)
from app.services import audit
from app.services import payables as ap_svc
from app.services.accounts_receivable import aging_bucket_for
from app.services.authority import require_module_access
from app.services.numbering import next_document_number
from app.services.tax import apply_gst

router = APIRouter(prefix="/api/accounts-payable", tags=["accounts-payable"])
MODULE = "accounts_payable"


def _supplier_or_404(db: Session, supplier_id: uuid.UUID, company_id: uuid.UUID) -> Supplier:
    s = db.get(Supplier, supplier_id)
    if not s or s.company_id != company_id:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return s


def _bill_or_404(db: Session, bill_id: uuid.UUID, company_id: uuid.UUID) -> SupplierInvoice:
    b = db.get(SupplierInvoice, bill_id)
    if not b or b.company_id != company_id:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")
    return b


# ---- Suppliers ------------------------------------------------------


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    q = db.query(Supplier).filter(Supplier.company_id == current_user.company_id)
    if not include_inactive:
        q = q.filter(Supplier.is_active)
    return q.order_by(Supplier.name).all()


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    supplier = Supplier(
        company_id=current_user.company_id,
        name=payload.name,
        email=payload.email,
        address=payload.address,
        gst_registration_no=payload.gst_registration_no,
        payment_terms_days=payload.payment_terms_days,
    )
    db.add(supplier)
    db.flush()
    audit.record(
        db,
        entity_type="supplier",
        entity_id=supplier.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={"name": payload.name, "payment_terms_days": payload.payment_terms_days},
    )
    db.commit()
    db.refresh(supplier)
    return supplier


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    supplier = _supplier_or_404(db, supplier_id, current_user.company_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("name", "email", "address", "gst_registration_no", "payment_terms_days", "is_active"):
        if field not in fields or getattr(supplier, field) == fields[field]:
            continue
        old_value[field] = getattr(supplier, field)
        new_value[field] = fields[field]
        setattr(supplier, field, fields[field])
    audit.record(
        db,
        entity_type="supplier",
        entity_id=supplier.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(supplier)
    return supplier


# ---- Purchase orders ------------------------------------------------


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    supplier_id: uuid.UUID | None = None,
    status: PurchaseOrderStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    q = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == current_user.company_id)
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    return q.order_by(PurchaseOrder.order_date.desc()).all()


@router.post("/purchase-orders", response_model=PurchaseOrderOut)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Raise a PO. GST is applied at the company's rate; whether it then
    needs the owner's approval is PUR-001's value test."""
    _supplier_or_404(db, payload.supplier_id, current_user.company_id)
    _code, _rate, gst, total = apply_gst(
        db, company_id=current_user.company_id, net_amount=Decimal(str(payload.amount_sgd))
    )

    needs_owner = ap_svc.po_needs_owner_approval(db, current_user.company_id, total)
    po = PurchaseOrder(
        company_id=current_user.company_id,
        supplier_id=payload.supplier_id,
        po_number=next_document_number(
            db, company_id=current_user.company_id, doc_kind="purchase_order"
        ),
        order_date=payload.order_date,
        description=payload.description,
        amount_sgd=Decimal(str(payload.amount_sgd)),
        gst_amount_sgd=gst,
        total_amount_sgd=total,
        status=PurchaseOrderStatus.PENDING_APPROVAL if needs_owner else PurchaseOrderStatus.DRAFT,
    )
    db.add(po)
    db.flush()
    audit.record(
        db,
        entity_type="purchase_order",
        entity_id=po.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{po.po_number}: {payload.description} SGD {total}",
        new_value={"po_number": po.po_number, "total_sgd": str(total), "status": po.status.value},
    )
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/approve", response_model=PurchaseOrderOut)
def approve_po(
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """PUR-001: value-based approval."""
    po = db.get(PurchaseOrder, po_id)
    if not po or po.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    try:
        ap_svc.approve_purchase_order(db, po, actor=current_user)
    except ap_svc.PayablesRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="purchase_order",
        entity_id=po.id,
        action="approved",
        actor_user_id=current_user.id,
        details=f"{po.po_number} SGD {po.total_amount_sgd}",
        new_value={"status": "approved"},
    )
    db.commit()
    db.refresh(po)
    return po


# ---- Supplier invoices (bills) --------------------------------------


@router.get("/bills", response_model=list[SupplierInvoiceOut])
def list_bills(
    supplier_id: uuid.UUID | None = None,
    status: BillStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    q = db.query(SupplierInvoice).filter(SupplierInvoice.company_id == current_user.company_id)
    if supplier_id:
        q = q.filter(SupplierInvoice.supplier_id == supplier_id)
    if status:
        q = q.filter(SupplierInvoice.status == status)
    return q.order_by(SupplierInvoice.invoice_date.desc()).all()


@router.post("/bills", response_model=SupplierInvoiceOut)
def create_bill(
    payload: SupplierInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Enter a supplier invoice. It is 2-way matched against its PO
    immediately (PUR-002); a match auto-approves it for payment
    (PUR-003), a mismatch becomes an exception."""
    _supplier_or_404(db, payload.supplier_id, current_user.company_id)
    net = Decimal(str(payload.amount_sgd))
    gst = Decimal(str(payload.gst_amount_sgd))

    bill = SupplierInvoice(
        company_id=current_user.company_id,
        supplier_id=payload.supplier_id,
        purchase_order_id=payload.purchase_order_id,
        bill_number=next_document_number(
            db, company_id=current_user.company_id, doc_kind="supplier_invoice"
        ),
        supplier_invoice_no=payload.supplier_invoice_no,
        invoice_date=payload.invoice_date,
        due_date=ap_svc.due_date_for_bill(db, payload.supplier_id, payload.invoice_date),
        description=payload.description,
        amount_sgd=net,
        gst_amount_sgd=gst,
        total_amount_sgd=net + gst,
    )
    db.add(bill)
    db.flush()

    try:
        ap_svc.match_bill_to_po(db, bill)
    except ap_svc.PayablesRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="supplier_invoice",
        entity_id=bill.id,
        action="received",
        actor_user_id=current_user.id,
        details=f"{bill.bill_number}: {bill.match_note}",
        new_value={
            "bill_number": bill.bill_number,
            "total_sgd": str(bill.total_amount_sgd),
            "match_status": bill.match_status.value,
            "status": bill.status.value,
        },
    )
    db.commit()
    db.refresh(bill)
    return bill


# ---- Payment vouchers -----------------------------------------------


@router.get("/payments", response_model=list[SupplierPaymentOut])
def list_supplier_payments(
    supplier_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    q = (
        db.query(SupplierPayment)
        .options(selectinload(SupplierPayment.allocations))
        .filter(SupplierPayment.company_id == current_user.company_id)
    )
    if supplier_id:
        q = q.filter(SupplierPayment.supplier_id == supplier_id)
    payments = q.order_by(SupplierPayment.payment_date.desc()).all()
    numbers = {
        b.id: b.bill_number
        for b in db.query(SupplierInvoice)
        .filter(SupplierInvoice.company_id == current_user.company_id)
        .all()
    }
    return [SupplierPaymentOut.from_model(p, numbers) for p in payments]


@router.post("/payments", response_model=SupplierPaymentOut)
def create_payment_voucher(
    payload: SupplierPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Raise a Payment Voucher (PV). Like AR, allocation is a separate
    manual decision -- money can be paid and allocated afterwards."""
    supplier = _supplier_or_404(db, payload.supplier_id, current_user.company_id)

    payment = SupplierPayment(
        company_id=current_user.company_id,
        supplier_id=payload.supplier_id,
        voucher_number=next_document_number(
            db, company_id=current_user.company_id, doc_kind="payment"
        ),
        payment_date=payload.payment_date,
        amount_sgd=Decimal(str(payload.amount_sgd)),
        method=payload.method,
        reference=payload.reference,
        notes=payload.notes,
        paid_by_user_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    for entry in payload.allocations:
        bill = _bill_or_404(db, entry.supplier_invoice_id, current_user.company_id)
        try:
            ap_svc.allocate_supplier_payment(db, payment, bill, Decimal(str(entry.amount_sgd)))
        except ap_svc.PayablesRuleViolation as e:
            raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="supplier_payment",
        entity_id=payment.id,
        action="recorded",
        actor_user_id=current_user.id,
        details=f"{payment.voucher_number}: SGD {payload.amount_sgd} to {supplier.name}",
        new_value={
            "voucher_number": payment.voucher_number,
            "amount_sgd": str(payload.amount_sgd),
            "supplier": supplier.name,
        },
    )
    db.commit()
    db.refresh(payment)
    return SupplierPaymentOut.from_model(payment)


@router.post("/payments/{payment_id}/allocate", response_model=SupplierPaymentOut)
def allocate_supplier_payment(
    payment_id: uuid.UUID,
    payload: SupplierAllocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    payment = (
        db.query(SupplierPayment)
        .options(selectinload(SupplierPayment.allocations))
        .filter(
            SupplierPayment.id == payment_id,
            SupplierPayment.company_id == current_user.company_id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment voucher not found")

    applied = []
    for entry in payload.allocations:
        bill = _bill_or_404(db, entry.supplier_invoice_id, current_user.company_id)
        try:
            ap_svc.allocate_supplier_payment(db, payment, bill, Decimal(str(entry.amount_sgd)))
        except ap_svc.PayablesRuleViolation as e:
            raise HTTPException(status_code=422, detail=str(e))
        applied.append(f"{bill.bill_number}={entry.amount_sgd}")

    audit.record(
        db,
        entity_type="supplier_payment",
        entity_id=payment.id,
        action="allocated",
        actor_user_id=current_user.id,
        details=", ".join(applied),
        new_value={"allocated_to": applied},
    )
    db.commit()
    db.refresh(payment)
    return SupplierPaymentOut.from_model(payment)


@router.get("/aging", response_model=APAgingReport)
def ap_aging(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """What we owe suppliers, bucketed by how far past due it is."""
    as_at = as_at or date.today()
    bills = (
        db.query(SupplierInvoice)
        .filter(
            SupplierInvoice.company_id == current_user.company_id,
            SupplierInvoice.status != BillStatus.PAID,
        )
        .all()
    )
    suppliers = {
        s.id: s.name
        for s in db.query(Supplier).filter(Supplier.company_id == current_user.company_id).all()
    }

    buckets: dict[uuid.UUID, dict[str, Decimal]] = {}
    for bill in bills:
        outstanding = bill.outstanding_sgd
        if outstanding <= 0:
            continue
        row = buckets.setdefault(
            bill.supplier_id,
            {"current": Decimal(0), "1_30": Decimal(0), "31_60": Decimal(0),
             "61_90": Decimal(0), "over_90": Decimal(0)},
        )
        row[aging_bucket_for(bill.due_date, as_at)] += outstanding

    rows = [
        APAgingRow(
            supplier_id=sid,
            supplier_name=suppliers.get(sid, "(unknown)"),
            current=float(b["current"]),
            days_1_30=float(b["1_30"]),
            days_31_60=float(b["31_60"]),
            days_61_90=float(b["61_90"]),
            over_90=float(b["over_90"]),
            total=float(sum(b.values())),
        )
        for sid, b in buckets.items()
    ]
    rows.sort(key=lambda r: r.total, reverse=True)
    return APAgingReport(as_at=as_at, rows=rows, total=sum(r.total for r in rows))
