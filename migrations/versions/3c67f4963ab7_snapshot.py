"""snapshot

Revision ID: 3c67f4963ab7
Revises: 61b4fd308352
Create Date: 2026-03-20 18:21:19.128062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3c67f4963ab7'
down_revision: Union[str, Sequence[str], None] = '61b4fd308352'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass