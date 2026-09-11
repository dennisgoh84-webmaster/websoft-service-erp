"""
General reference-data lookups: Nationality, Country, State, Area Code,
Currency codes. These are universal facts (a country's name doesn't
differ per company), so -- unlike almost everything else in this app --
SetupListItem rows are NOT scoped by company_id; every company shares
one global list per `list_type`.

One generic table rather than four/five near-identical ones (each just
a code + a name) per CLAUDE.md's "modular and maintainable" -- a new
kind of simple code list is a data row here, not a new table/migration.
`parent_code` is the one hierarchy this needs (a State belongs to a
Country), stored as a plain string reference to another row's `code`
rather than a hard FK, since the parent can be in a different
`list_type` and country codes are stable enough not to need referential
enforcement here.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SetupListType(str, enum.Enum):
    NATIONALITY = "nationality"
    COUNTRY = "country"
    STATE = "state"  # parent_code = the owning Country's code
    AREA_CODE = "area_code"
    CURRENCY = "currency"


class SetupListItem(Base):
    __tablename__ = "setup_list_items"
    __table_args__ = (
        UniqueConstraint("list_type", "code", name="uq_setup_list_item_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    list_type: Mapped[SetupListType] = mapped_column(
        Enum(SetupListType, name="setup_list_type"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
