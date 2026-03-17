"""add counterparty_legal_entity_id

Revision ID: 2571777c8159
Revises: 46a4f63b07cc
Create Date: 2026-03-17 12:11:20.390821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2571777c8159'
down_revision: Union[str, Sequence[str], None] = '46a4f63b07cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'bank_operations',
        sa.Column('counterparty_legal_entity_id', sa.UUID(), nullable=True)
    )

    op.create_foreign_key(
        None,
        'bank_operations',
        'legal_entities',
        ['counterparty_legal_entity_id'],
        ['id']
    )


def downgrade():
    op.drop_constraint(None, 'bank_operations', type_='foreignkey')
    op.drop_column('bank_operations', 'counterparty_legal_entity_id')
