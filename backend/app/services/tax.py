"""
GST calculation.

Confirmed 2026-09-10: Webmaster Consultancy is GST-registered and its
services are standard-rated. The rate itself is data (app/models/tax.py)
so a future rate change is a configuration change, and each invoice
records the rate it was actually raised at.
"""
import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.tax import DEFAULT_TAX_CODE, TaxCode


def get_tax_code(db: Session, company_id: uuid.UUID, code: str | None = None) -> TaxCode | None:
    return (
        db.query(TaxCode)
        .filter(
            TaxCode.company_id == company_id,
            TaxCode.code == (code or DEFAULT_TAX_CODE),
            TaxCode.is_active,
        )
        .first()
    )


def gst_for(net_amount: Decimal, rate_percent: Decimal) -> Decimal:
    """GST on a net amount, rounded to cents (half up)."""
    return (Decimal(net_amount) * Decimal(rate_percent) / Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def apply_gst(
    db: Session, *, company_id: uuid.UUID, net_amount: Decimal, code: str | None = None
) -> tuple[str, Decimal, Decimal, Decimal]:
    """Returns (tax_code, rate_percent, gst_amount, total_including_gst).

    If no tax code is configured for the company, GST is zero and the
    invoice is raised net-only -- an unconfigured company should not have
    tax silently invented for it.
    """
    tax_code = get_tax_code(db, company_id, code)
    if tax_code is None:
        return (code or DEFAULT_TAX_CODE, Decimal("0.00"), Decimal("0.00"), Decimal(net_amount))

    gst = gst_for(net_amount, tax_code.rate_percent)
    return (tax_code.code, Decimal(tax_code.rate_percent), gst, Decimal(net_amount) + gst)
