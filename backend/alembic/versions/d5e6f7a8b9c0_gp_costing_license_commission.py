"""Sales GP costing, contract-product license type, commission settings

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-12

Confirmed with Dennis, 2026-09-12 (see docs/open-business-decisions.md
#32-#34):
- QuotationLine.cost_sgd / Invoice.cost_sgd: product cost per line/
  invoice, so a GP report can compare cost against revenue.
- ContractProduct.license_type / number_of_licenses: LOCAL/RDP/WEB
  license tracking per product a contract covers.
- commission_settings: a per-company, admin-editable commission rate
  (percentage of GP) -- the formula is decided, the rate is not
  invented here.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None

# Labels are the Python enum's MEMBER NAMES (uppercase), not its lowercase
# values -- SQLAlchemy's Enum column type binds/reads by member name by
# default (see e.g. contract_status: ContractStatus.DRAFT = "draft" is
# stored as 'DRAFT'), so the Postgres type must match that convention.
license_deployment_type = postgresql.ENUM(
    "LOCAL", "RDP", "WEB", name="license_deployment_type"
)


def upgrade() -> None:
    op.add_column("quotation_lines", sa.Column("cost_sgd", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("cost_sgd", sa.Numeric(12, 2), nullable=True))

    license_deployment_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "contract_products",
        sa.Column("license_type", license_deployment_type, nullable=True),
    )
    op.add_column("contract_products", sa.Column("number_of_licenses", sa.Integer(), nullable=True))

    op.create_table(
        "commission_settings",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rate_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )


def downgrade() -> None:
    op.drop_table("commission_settings")
    op.drop_column("contract_products", "number_of_licenses")
    op.drop_column("contract_products", "license_type")
    license_deployment_type.drop(op.get_bind(), checkfirst=True)
    op.drop_column("invoices", "cost_sgd")
    op.drop_column("quotation_lines", "cost_sgd")
