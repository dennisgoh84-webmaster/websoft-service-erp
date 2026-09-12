"""
Document numbering.

A Singapore tax invoice must carry an identifying number, and those
numbers must not repeat or collide. Numbers are allocated per company
per year from a counter row that is locked while it is incremented, so
two invoices raised at the same moment cannot take the same number.

The format (INV-2026-0001) is a starting convention, not a rule anyone
confirmed -- IRAS requires invoices to be serially numbered but does not
mandate a layout, so this can change if Dennis wants a different one.
"""
import uuid
from datetime import date

from sqlalchemy import Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base


class DocumentSequence(Base):
    """Last number issued for a (company, document kind, year)."""

    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("company_id", "doc_kind", "year", name="uq_document_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_kind: Mapped[str] = mapped_column(String(30), nullable=False)  # e.g. "invoice"
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DocumentNumberFormat(Base):
    """Per-company, per-document-kind override of the running number's
    prefix ("front alphabet") and digit padding -- confirmed 2026-09-11:
    "allow customization of the running number formatting and front
    alphabet." A doc_kind with no row here keeps using the built-in
    default (PREFIXES below, 4-digit padding, year included) -- adding
    this table changes nothing for a doc_kind nobody has customized.

    Changing a format only affects numbers issued AFTER the change --
    every document already numbered keeps the text it was given
    (CLAUDE.md: never modify existing business records)."""

    __tablename__ = "document_number_formats"
    __table_args__ = (
        UniqueConstraint("company_id", "doc_kind", name="uq_document_number_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    # Digits the running number is zero-padded to, e.g. 4 -> "0001".
    number_length: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    include_year: Mapped[bool] = mapped_column(nullable=False, default=True)


PREFIXES = {
    "invoice": "INV",       # sales tax invoice
    "receipt": "RV",        # receipt voucher -- money in
    "payment": "PV",        # payment voucher -- money out
    "journal": "JV",        # journal voucher -- manual adjustment
    "purchase_order": "PO",
    "supplier_invoice": "BILL",
    "quotation": "QUO",      # sales quotation
    # Confirmed 2026-09-11: "all main documents need to have a system
    # generated running number to be controlled" -- these three
    # operational documents previously had none.
    "contract": "CON",       # service contract
    "job_order": "JO",
    "service_record": "SR",
    "bank_transaction": "BT",  # Bank Book entry, separate from the GL's JV/RV/PV
}


def next_document_number(
    db: Session, *, company_id: uuid.UUID, doc_kind: str, on: date | None = None
) -> str:
    """Allocate the next number for this company/kind/year.

    The counter row is locked for the duration of the transaction, so
    concurrent invoice creation serialises here rather than producing
    duplicate numbers.
    """
    year = (on or date.today()).year

    row = (
        db.query(DocumentSequence)
        .filter(
            DocumentSequence.company_id == company_id,
            DocumentSequence.doc_kind == doc_kind,
            DocumentSequence.year == year,
        )
        .with_for_update()
        .first()
    )
    if row is None:
        row = DocumentSequence(company_id=company_id, doc_kind=doc_kind, year=year, last_number=0)
        db.add(row)
        db.flush()
        # Re-read under lock in case another transaction inserted first.
        row = (
            db.query(DocumentSequence)
            .filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.doc_kind == doc_kind,
                DocumentSequence.year == year,
            )
            .with_for_update()
            .one()
        )

    row.last_number += 1
    db.flush()
    return format_document_number(db, company_id=company_id, doc_kind=doc_kind, year=year, number=row.last_number)


def format_document_number(
    db: Session, *, company_id: uuid.UUID, doc_kind: str, year: int, number: int
) -> str:
    """Render a document number using this company's customization for
    `doc_kind` (Document Control), if any, else the built-in default.
    Split out from next_document_number so Document Control's preview
    of "what would the next number look like" can call it without
    consuming a number."""
    fmt = (
        db.query(DocumentNumberFormat)
        .filter(
            DocumentNumberFormat.company_id == company_id,
            DocumentNumberFormat.doc_kind == doc_kind,
        )
        .first()
    )
    if fmt:
        prefix, number_length, include_year = fmt.prefix, fmt.number_length, fmt.include_year
    else:
        prefix, number_length, include_year = PREFIXES.get(doc_kind, doc_kind.upper()[:3]), 4, True

    seq = f"{number:0{number_length}d}"
    return f"{prefix}-{year}-{seq}" if include_year else f"{prefix}-{seq}"
