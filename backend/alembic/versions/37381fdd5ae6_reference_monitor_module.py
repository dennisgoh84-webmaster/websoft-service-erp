"""Reference Monitor: GL sub-codes under one Chart of Accounts row

Revision ID: 37381fdd5ae6
Revises: 95d1cda707de
Create Date: 2026-09-12

Adds the `reference_codes` table (see app/models/reference_codes.py) --
a plain child of one Account row, e.g. several sub-codes
(SLS-WEBSOFT-IMPLEMENTATION, SLS-WEBSOFT-SERVICE, ...) all posting to
the same GL code -- plus the two columns that let a document line
capture one: `products.default_reference_code_id` (preset on the
product) and `quotation_lines.reference_code_id` (captured on the
line, auto-filled from the product's default but overridable). Both FK
columns are nullable: existing products and quotation lines are simply
unclassified until someone assigns them, and QuotationLine.description
already carries the printed text regardless.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "37381fdd5ae6"
down_revision = "95d1cda707de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.UniqueConstraint("company_id", "code", name="uq_reference_code"),
    )

    op.add_column(
        "products",
        sa.Column("default_reference_code_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_default_reference_code_id",
        "products",
        "reference_codes",
        ["default_reference_code_id"],
        ["id"],
    )

    op.add_column(
        "quotation_lines",
        sa.Column("reference_code_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_quotation_lines_reference_code_id",
        "quotation_lines",
        "reference_codes",
        ["reference_code_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotation_lines_reference_code_id", "quotation_lines", type_="foreignkey")
    op.drop_column("quotation_lines", "reference_code_id")

    op.drop_constraint("fk_products_default_reference_code_id", "products", type_="foreignkey")
    op.drop_column("products", "default_reference_code_id")

    op.drop_table("reference_codes")
