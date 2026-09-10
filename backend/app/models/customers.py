"""Customer Management models.

Field set follows the Odoo Contacts/Customer card (screenshot provided
2026-09-10), since Websoft ERP is meant to eventually replace it -- see
CLAUDE.md's Odoo replacement strategy and historical-data migration
notes. Two fields on that card needed a confirmed business meaning
rather than a guess:
  - "Customer ID" -> `legacy_customer_code`: a manual free-text field to
    carry the customer's existing Odoo code, for matching during the
    eventual data migration. Not auto-generated, not validated.
  - "Exclude Auto Sent" -> `exclude_auto_sent`: stored now so it
    carries over correctly, but nothing reads it yet -- there is no
    automated invoice/reminder emailing built in this system yet.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CustomerType(str, enum.Enum):
    individual = "individual"
    company = "company"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)

    # Most customers of a B2B services company are companies, so that is
    # the practical default for the picker; it is always explicit and
    # editable, never inferred from other fields.
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, name="customer_type"), nullable=False, default=CustomerType.company
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Carries the customer's code from the Odoo system being replaced,
    # for matching during the eventual historical-data migration.
    # Manual, optional, unvalidated -- confirmed 2026-09-10.
    legacy_customer_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Quick top-level contact name (Odoo's "Contact Person" field), kept
    # separate from the full Contact list below -- this is a one-line
    # convenience, not a substitute for managing actual contact people.
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)

    uen: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The customer's own GST registration number (distinct from this
    # company's own gst_registration_no on the Company model).
    gst_registration_no: Mapped[str | None] = mapped_column(String(50), nullable=True)

    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured address (replaces the old single free-text
    # billing_address column -- see migration for the backfill).
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Simple free-text, comma-separated -- no dedicated tag table exists
    # elsewhere in the system yet, so this matches that (e.g. "B2B, VIP").
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Reserved: no automated invoice/reminder emailing exists yet, so
    # this flag isn't read by anything today. See module docstring.
    exclude_auto_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AR: how long this customer has to pay, in days from the invoice
    # date. Confirmed 2026-09-10 that terms vary per customer, so there
    # is deliberately no company-wide default -- null means terms have
    # not been agreed yet, and the invoice carries no due date rather
    # than the system inventing one.
    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contacts: Mapped[list["Contact"]] = relationship(back_populates="customer")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Soft-delete, matching every other master record in this system
    # (Customer, Supplier, Staff, Account, Company) -- never hard-delete
    # a business contact, just stop showing it as active.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer: Mapped["Customer"] = relationship(back_populates="contacts")
