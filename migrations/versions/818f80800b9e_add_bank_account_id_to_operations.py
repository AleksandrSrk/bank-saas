"""add bank_account_id to operations

Revision ID: 818f80800b9e
Revises: a16a535e2aca
Create Date: 2026-03-12 15:44:59.220921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '818f80800b9e'
down_revision: Union[str, Sequence[str], None] = 'a16a535e2aca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
def upgrade():
    op.add_column(
        "bank_operations",
        sa.Column("bank_account_id", sa.UUID(), nullable=True)
    )

    op.create_foreign_key(
        "fk_bank_operations_account",
        "bank_operations",
        "bank_accounts",
        ["bank_account_id"],
        ["id"]
    )