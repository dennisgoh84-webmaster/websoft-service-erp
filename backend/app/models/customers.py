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

Branches and Customer Groups (added 2026-09-10) answer two follow-up
asks:
  - "Company with branches" -> `Branch`: a customer (usually
    customer_type=company) can have multiple branch locations, each
    with its own address/telephone/branch code. A branch is a location
    of the SAME legal entity/customer -- it doesn't bill separately.
  - "Group of companies... how do I group them?" -> `CustomerGroup`:
    confirmed 2026-09-10 as a lightweight tag, not a merged account --
    each of (e.g.) 5 separate company names stays its own Customer
    record with its own contracts/invoices/AR, but can be tagged with
    a shared CustomerGroup so the Customer list can be filtered/found
    by group. This is deliberately not a parent/child billing
    hierarchy; that would be a much bigger, undecided feature
    (consolidated statements etc.) -- see open-business-decisions.md.
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


class CustomerGroup(Base):
    """A lightweight tag linking separate Customer records that belong
    to the same group of companies (e.g. a holding structure). Each
    tagged Customer remains its own full account -- see module
    docstring. Company-scoped like every other master record."""

    __tablename__ = "customer_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customers: Mapped[list["Customer"]] = relationship(back_populates="customer_group")


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

    # Optional tag linking this customer to others in the same group of
    # companies. See CustomerGroup docstring -- confirmed 2026-09-10 as
    # a tag, not a shared billing account.
    customer_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_groups.id"), nullable=True
    )

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
    # billing_address column -- see migration for the backfill). This is
    # the main/registered address; branch-specific addresses live on
    # Branch below.
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Simple free-text, comma-separated -- no dedicated tag table exists
    # elsewhere in the system yet, so this matches that (e.g. "B2B, VIP").
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Confirmed 2026-09-11: customer grouping by industry. A loose
    # reference to SetupListItem.code where list_type=INDUSTRY (same
    # pattern as SetupListItem.parent_code) rather than a hard FK, kept
    # optional -- not every customer's industry is known up front.
    industry_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Reserved: no automated invoice/reminder emailing exists yet, so
    # this flag isn't read by anything today. See module docstring.
    exclude_auto_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Internal-only notes, never shown on any customer-facing document.
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Billing-specific notes (e.g. "requires PO number on every invoice") --
    # kept separate from `memo` since billing/AR staff and general staff
    # often need different notes surfaced to them.
    billing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AR: how long this customer has to pay, in days from the invoice
    # date. Confirmed 2026-09-10 that terms vary per customer, so there
    # is deliberately no company-wide default -- null means terms have
    # not been agreed yet, and the invoice carries no due date rather
    # than the system inventing one.
    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Role flags (2026-09-12: "when talking about supplier, remember to
    # use the same company/individual file, do not add or reinvent a new
    # one again") -- one Company/Individual master now covers both roles
    # instead of a separate Supplier table. A record can be either, or
    # both (a contact who is both a customer and a vendor). Existing
    # records default to is_customer=True (that is what this table held
    # before suppliers were merged in); is_supplier is opt-in per record,
    # ticked on the ones migrated from the old suppliers table.
    is_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contacts: Mapped[list["Contact"]] = relationship(back_populates="customer")
    branches: Mapped[list["Branch"]] = relationship(back_populates="customer")
    customer_group: Mapped["CustomerGroup | None"] = relationship(back_populates="customers")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # A direct dial line, distinct from the general `phone` above (which
    # may be a mobile or a shared extension).
    direct_line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Soft-delete, matching every other master record in this system
    # (Customer, Supplier, Staff, Account, Company) -- never hard-delete
    # a business contact, just stop showing it as active.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer: Mapped["Customer"] = relationship(back_populates="contacts")


class Branch(Base):
    """A branch location of a Customer -- same legal entity/account,
    different address. Not a separate billing account (that would be a
    separate Customer record); just where the customer's contacts and
    correspondence for that location live. See module docstring."""

    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    branch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer: Mapped["Customer"] = relationship(back_populates="branches")


class CustomerRelationship(Base):
    """A link from one Customer to another Customer or Contact --
    "company / individual" relationships confirmed 2026-09-11, distinct
    from CustomerGroup above (a same-group *tag*, not a typed link
    between two specific records). Covers all three levels the request
    named without needing a separate field for which: company-level and
    individual-level are both just to_customer_id (the level follows
    from that Customer's own customer_type), and company-contact-level
    is to_contact_id (exactly one of the two is set).

    Undirected/symmetric by default (confirmed as a pragmatic default,
    not an explicitly confirmed rule -- see
    docs/open-business-decisions.md): one row, shown the same way on
    both ends, rather than a directional pair like "Parent of" /
    "Subsidiary of". relationship_type is free text (no fixed taxonomy
    was given), matching how Customer.tags is already free text
    elsewhere on this model."""

    __tablename__ = "customer_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    from_customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    to_customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    to_contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soft-delete, matching every other master record here.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    from_customer: Mapped["Customer"] = relationship(foreign_keys=[from_customer_id])
    to_customer: Mapped["Customer | None"] = relationship(foreign_keys=[to_customer_id])
    to_contact: Mapped["Contact | None"] = relationship(foreign_keys=[to_contact_id])
