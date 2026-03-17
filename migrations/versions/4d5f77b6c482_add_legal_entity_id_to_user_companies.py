"""add legal_entity_id to user_companies

Revision ID: 4d5f77b6c482
Revises: 9b9c0e0060dd
Create Date: 2026-03-17 10:30:50.631261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d5f77b6c482'
down_revision: Union[str, Sequence[str], None] = '9b9c0e0060dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.add_column(
        "user_companies",
        sa.Column("legal_entity_id", sa.UUID(), nullable=True)
    )


def downgrade():

    op.drop_column("user_companies", "legal_entity_id")
