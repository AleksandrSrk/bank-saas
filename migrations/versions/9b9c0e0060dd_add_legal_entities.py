"""add legal_entities

Revision ID: 9b9c0e0060dd
Revises: 3d25b827ad60
Create Date: 2026-03-17 10:28:11.200649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b9c0e0060dd'
down_revision: Union[str, Sequence[str], None] = '3d25b827ad60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "legal_entities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("inn", sa.String(), nullable=False, unique=True)
    )


def downgrade() -> None:

    op.drop_table("legal_entities")
