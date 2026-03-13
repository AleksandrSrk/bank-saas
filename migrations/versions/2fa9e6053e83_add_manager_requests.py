"""add manager requests

Revision ID: 2fa9e6053e83
Revises: 0686d7bc2a01
Create Date: 2026-03-13 09:47:31.921159
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2fa9e6053e83"
down_revision: Union[str, Sequence[str], None] = "0686d7bc2a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("manager_requests")