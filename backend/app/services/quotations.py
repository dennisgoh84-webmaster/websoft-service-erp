"""Sales Quotation business logic: totals and the accept -> auto-Contract
conversion. See app/models/quotations.py's docstring for the confirmed
splitting rule (hourly lines -> one Service Support contract; every
other line -> one Annual contract)."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.contracts import ContractKind
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


def _is_hourly(unit_of_measure: str | None) -> bool:
    return (unit_of_measure or "").strip().lower() in ("hour", "hours")


def accept_quotation(db: Session, quotation: Quotation, *, actor_user_id: uuid.UUID) -> str:
    """Marks the quotation Accepted and attempts to auto-create
    Contract(s) from it -- confirmed 2026-09-10: a quotation's lines
    split by unit of measure into up to two separate contracts, never
    one blending both:
      - Lines whose unit is "Hours"/"Hour" -> one SERVICE_SUPPORT
        contract, summing their hours and their value. SRV-002/012's
        10-hour minimum still applies with no override, so this half
        may legitimately not convert if there aren't enough hours.
      - Every other line -> one ANNUAL contract (term-only, standard
        12-month duration), summing their value. No minimum applies.
    A quotation with only one kind of line converts to just that one
    contract; a quotation with neither (empty, in practice impossible
    since a quotation needs at least one line) converts to neither.
    Returns a message describing exactly what happened to each half.
    """
    quotation.status = QuotationStatus.accepted

    hourly_lines = [line for line in quotation.lines if _is_hourly(line.unit_of_measure)]
    other_lines = [line for line in quotation.lines if not _is_hourly(line.unit_of_measure)]

    messages: list[str] = []

    if hourly_lines:
        hourly_qty = sum((line.quantity for line in hourly_lines), Decimal("0"))
        hourly_value = sum((line.line_total_sgd for line in hourly_lines), Decimal("0"))
        try:
            contract = create_contract(
                db,
                company_id=quotation.company_id,
                customer_id=quotation.customer_id,
                contract_kind=ContractKind.SERVICE_SUPPORT,
                contracted_hours=float(hourly_qty),
                contract_value_sgd=float(hourly_value),
                start_date=date.today(),
                actor_user_id=actor_user_id,
            )
            quotation.converted_contract_id = contract.id
            messages.append(f"Service Support contract created ({float(hourly_qty):g} hrs).")
        except ContractRuleViolation as exc:
            messages.append(f"Hourly lines not converted to a contract: {exc}")

    if other_lines:
        other_value = sum((line.line_total_sgd for line in other_lines), Decimal("0"))
        annual_contract = create_contract(
            db,
            company_id=quotation.company_id,
            customer_id=quotation.customer_id,
            contract_kind=ContractKind.ANNUAL,
            contracted_hours=0,
            contract_value_sgd=float(other_value),
            start_date=date.today(),
            actor_user_id=actor_user_id,
        )
        quotation.converted_annual_contract_id = annual_contract.id
        messages.append(f"Annual contract created (SGD {other_value:.2f}, 12-month term).")

    message = "Quotation accepted. " + " ".join(messages) if messages else "Quotation accepted."

    audit.record(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        action="accepted",
        actor_user_id=actor_user_id,
        details=message,
    )
    return message
