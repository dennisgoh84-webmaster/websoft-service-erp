"""rename Customer entity/tables to Company/Individual

Revision ID: 95d1cda707de
Revises: e2f33975e091
Create Date: 2026-09-12

Renames the DB tables backing the `Customer` model (now `CompanyIndividual`,
see app/models/company_individuals.py) to match -- 2026-09-12: "change all
Customer labeling in the source code to Company/Individual also... if not
later more confusing." Every foreign key column pointing at these tables
(`customer_id`, `supplier_id`, `from_customer_id`, `to_customer_id`,
`customer_group_id`, etc.) is deliberately left unchanged: only the
target table itself moves, matching the precedent already set when the
`suppliers` table was folded into `customers` in `e2f33975e091` (that
migration kept `supplier_id` pointing at the renamed target). The
`customer_type` Postgres enum and every snake_case FK/role column
(`is_customer`, `legacy_customer_code`, ...) stay as-is for the same
reason -- see app/models/company_individuals.py's module docstring.

Also renames the Module Control key `customer_management` ->
`company_individual_management` (an internal permission-key identifier,
not the module's confirmed display name "Customer Management", which is
left as-is -- see docs/module-map.md #4) across `modules`,
`company_modules`, and `group_module_authorities`, since a table rename
without it would leave every existing Group Authority row pointing at a
now-nonexistent module key.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "95d1cda707de"
down_revision = "e2f33975e091"
branch_labels = None
depends_on = None

OLD_MODULE_KEY = "customer_management"
NEW_MODULE_KEY = "company_individual_management"


def _rename_module_key(old_key: str, new_key: str) -> None:
    """Renames a Module's primary-key string in place. `modules.key` is
    referenced by FK from `company_modules.module_key` and
    `group_module_authorities.module_key` with no ON UPDATE CASCADE, so a
    plain UPDATE on the parent row would violate those FKs while children
    still point at the old value. Insert-repoint-delete instead, all in
    this migration's single transaction."""
    op.execute(
        f"""
        INSERT INTO modules (key, name, description, is_built)
        SELECT '{new_key}', name, description, is_built
        FROM modules WHERE key = '{old_key}'
        """
    )
    op.execute(
        f"UPDATE company_modules SET module_key = '{new_key}' WHERE module_key = '{old_key}'"
    )
    op.execute(
        f"UPDATE group_module_authorities SET module_key = '{new_key}' WHERE module_key = '{old_key}'"
    )
    op.execute(f"DELETE FROM modules WHERE key = '{old_key}'")


def upgrade() -> None:
    op.rename_table("customer_groups", "company_individual_groups")
    op.rename_table("customers", "company_individuals")
    op.rename_table("customer_relationships", "company_individual_relationships")
    _rename_module_key(OLD_MODULE_KEY, NEW_MODULE_KEY)


def downgrade() -> None:
    _rename_module_key(NEW_MODULE_KEY, OLD_MODULE_KEY)
    op.rename_table("company_individual_relationships", "customer_relationships")
    op.rename_table("company_individuals", "customers")
    op.rename_table("company_individual_groups", "customer_groups")
