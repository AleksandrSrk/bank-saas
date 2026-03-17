"""add is_internal

Revision ID: 46a4f63b07cc
Revises: 4d5f77b6c482
Create Date: 2026-03-17 11:56:34.636184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46a4f63b07cc'
down_revision: Union[str, Sequence[str], None] = '4d5f77b6c482'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'bank_operations',
        sa.Column('is_internal', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('bank_operations', 'is_internal')
