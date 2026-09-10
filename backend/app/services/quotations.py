"""Sales Quotation business logic: totals and the accept -> auto-Contract
conversion. See app/models/quotations.py's docstring for the one still-
open business decision this touches (how mixed-unit lines map onto a
Contract's required hours)."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.quotations import Quotation, QuotationStatus
from app.services import audit
from app.services import tax as tax_svc
from app.services.contracts import ContractRuleViolation, create_contract


def recompute_totals(db: Session, quotation: Quotation) -> None:
    """Recomputes the document-level net/GST/total from its lines.
    Single GST rate per document, same pattern as Invoice."""
    net = sum((line.line_total_sgd for line in quotation.lines), Decimal("0"))
    tax_code, rate, gst, total = tax_svc.apply_gst(
        db, company_id=quotation.company_id, net_amount=net
    )
    quotation.amount_sgd = net
    quotation.tax_code = tax_code
    quotation.gst_rate = rate
    quotation.gst_amount_sgd = gst
    quotation.total_amount_sgd = total


def accept_quotation(
    db: Session, quotation: Quotation, *, actor_user_id: uuid.UUID
) -> str:
    """Marks the quotation Accepted and attempts to auto-create a draft
    Service Contract from it. Returns a message explaining what
    happened -- conversion can legitimately not occur: only lines whose
    unit_of_measure is "Hours"/"Hour" count toward the contract's
    required hours, and SRV-002/012's 10-hour minimum has no override,
    so a quotation with no (or too few) hourly lines is accepted but
    stays unconverted rather than producing an invalid contract."""
    quotation.status = QuotationStatus.accepted

    hourly_qty = sum(
        (
            line.quantity
            for line in quotation.lines
            if (line.unit_of_measure or "").strip().lower() in ("hour", "hours")
        ),
        Decimal("0"),
    )

    message = "Quotation accepted."
    try:
        contract = create_contract(
            db,
            company_id=quotation.company_id,
            customer_id=quotation.customer_id,
            contracted_hours=float(hourly_qty),
            contract_value_sgd=float(quotation.amount_sgd),
            start_date=date.today(),
            actor_user_id=actor_user_id,
        )
        quotation.converted_contract_id = contract.id
        message = f"Quotation accepted and converted to a draft contract ({float(hourly_qty):g} hrs)."
    except ContractRuleViolation as exc:
        message = f"Quotation accepted. Not auto-converted to a contract: {exc}"

    audit.record(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        action="accepted",
        actor_user_id=actor_user_id,
        details=message,
    )
    return message
