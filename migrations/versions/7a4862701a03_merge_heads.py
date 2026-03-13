"""merge heads

Revision ID: 7a4862701a03
Revises: 818f80800b9e, bff3debb657a
Create Date: 2026-03-13 09:30:02.012474

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a4862701a03'
down_revision: Union[str, Sequence[str], None] = ('818f80800b9e', 'bff3debb657a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
