"""group per company: move group_id to user_company_access

Revision ID: 3af20a7d4dec
Revises: 051c0726fa57
Create Date: 2026-09-10 03:36:35.523016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3af20a7d4dec'
down_revision: Union[str, Sequence[str], None] = '051c0726fa57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move the Group assignment from the user onto the user's company
    access row, so a staff member holds a Group *per company*.

    Existing assignments must survive, so the data is carried across
    before the old column is dropped: every user gets an access row for
    the company they are in (multi-company access rows didn't exist
    before this feature), and their current Group is copied onto it --
    but only where that Group actually belongs to that company, since a
    Group is meaningless outside its own entity.
    """
    op.add_column('user_company_access', sa.Column('group_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_user_company_access_group', 'user_company_access', 'groups', ['group_id'], ['id']
    )

    # 1. Make sure every user has an access row for their own company.
    op.execute(
        "INSERT INTO user_company_access (id, user_id, company_id) "
        "SELECT gen_random_uuid(), u.id, u.company_id FROM users u "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM user_company_access uca "
        "  WHERE uca.user_id = u.id AND uca.company_id = u.company_id"
        ")"
    )

    # 2. Carry each user's Group onto the matching company's access row.
    op.execute(
        "UPDATE user_company_access uca SET group_id = u.group_id "
        "FROM users u, groups g "
        "WHERE u.id = uca.user_id "
        "  AND u.group_id IS NOT NULL "
        "  AND g.id = u.group_id "
        "  AND g.company_id = uca.company_id"
    )

    # 3. Only now is the old column redundant.
    op.drop_constraint(op.f('users_group_id_fkey'), 'users', type_='foreignkey')
    op.drop_column('users', 'group_id')


def downgrade() -> None:
    """Collapse back to one Group per user, taking the Group from the
    company each user is currently in. Groups they held in *other*
    companies cannot be represented by the old shape and are lost."""
    op.add_column('users', sa.Column('group_id', sa.UUID(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('users_group_id_fkey'), 'users', 'groups', ['group_id'], ['id'])
    op.execute(
        "UPDATE users u SET group_id = uca.group_id "
        "FROM user_company_access uca "
        "WHERE uca.user_id = u.id AND uca.company_id = u.company_id"
    )
    op.drop_constraint(
        'fk_user_company_access_group', 'user_company_access', type_='foreignkey'
    )
    op.drop_column('user_company_access', 'group_id')
