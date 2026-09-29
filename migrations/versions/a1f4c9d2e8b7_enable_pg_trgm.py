"""enable pg_trgm extension

Revision ID: a1f4c9d2e8b7
Revises: 785db2176d7a
Create Date: 2026-09-29 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1f4c9d2e8b7'
down_revision: Union[str, Sequence[str], None] = '785db2176d7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
