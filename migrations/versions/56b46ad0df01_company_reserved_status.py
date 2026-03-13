"""company reserved status

Revision ID: 56b46ad0df01
Revises: c8ab8152fff1
Create Date: 2026-03-13

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '56b46ad0df01'
down_revision: Union[str, Sequence[str], None] = 'c8ab8152fff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # 1. добавляем колонку status
    op.add_column(
        'companies',
        sa.Column('status', sa.String(length=50), nullable=True)
    )

    # 2. делаем name nullable
    op.alter_column(
        'companies',
        'name',
        existing_type=sa.String(length=255),
        nullable=True
    )


def downgrade() -> None:

    # возвращаем name NOT NULL
    op.alter_column(
        'companies',
        'name',
        existing_type=sa.String(length=255),
        nullable=False
    )

    # удаляем status
    op.drop_column('companies', 'status')