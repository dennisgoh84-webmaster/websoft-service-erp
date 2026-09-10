"""
Billing business logic -- BILL-001 (annual upfront), BILL-002 (no
approval needed), BILL-005 (revenue recognized on invoice), and SRV-008
(excess usage billed at the contract's own blended rate).
"""
import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceType
from app.models.contracts import Contract, ExcessUsageRecord
from app.services import audit


def issue_contract_annual_invoice(
    db: Session, contract: Contract, *, actor_user_id: uuid.UUID
) -> Invoice:
    """BILL-001: full 12-month contract value, billed at contract
    start/renewal. BILL-002: no approval required -- issued directly."""
    invoice = Invoice(
        company_id=contract.company_id,
        customer_id=contract.customer_id,
        contract_id=contract.id,
        invoice_type=InvoiceType.CONTRACT_ANNUAL,
        description=(
            f"Annual service contract ({contract.start_date.isoformat()} to "
            f"{contract.end_date.isoformat()})"
        ),
        amount_sgd=contract.contract_value_sgd,
    )
    db.add(invoice)
    db.flush()

    audit.record(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="issued",
        actor_user_id=actor_user_id,
        details=f"invoice_type=contract_annual, contract_id={contract.id}",
    )
    return invoice


def blended_rate_per_hour(contract: Contract) -> Decimal:
    """SRV-008: contract value divided by contracted hours."""
    contracted_hours = Decimal(contract.contracted_minutes) / Decimal(60)
    return (Decimal(contract.contract_value_sgd) / contracted_hours).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def issue_excess_usage_invoice(
    db: Session,
    excess_record: ExcessUsageRecord,
    contract: Contract,
    *,
    actor_user_id: uuid.UUID,
) -> Invoice:
    """SRV-008: billable excess usage is charged at the contract's own
    blended rate, no customer pre-approval required."""
    rate = blended_rate_per_hour(contract)
    excess_hours = Decimal(excess_record.excess_minutes) / Decimal(60)
    amount = (rate * excess_hours).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    invoice = Invoice(
        company_id=contract.company_id,
        customer_id=contract.customer_id,
        contract_id=contract.id,
        excess_usage_record_id=excess_record.id,
        invoice_type=InvoiceType.EXCESS_USAGE,
        description=(
            f"Excess support usage beyond contracted hours "
            f"({excess_hours} hrs @ SGD {rate}/hr)"
        ),
        amount_sgd=amount,
    )
    db.add(invoice)
    excess_record.invoiced = True
    db.flush()

    audit.record(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="issued",
        actor_user_id=actor_user_id,
        details=f"invoice_type=excess_usage, excess_usage_record_id={excess_record.id}",
    )
    return invoice
