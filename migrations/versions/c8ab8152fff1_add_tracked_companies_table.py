"""add tracked_companies table

Revision ID: c8ab8152fff1
Revises: 2fa9e6053e83
Create Date: 2026-03-13 12:40:23.393766
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8ab8152fff1'
down_revision: Union[str, Sequence[str], None] = '2fa9e6053e83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "tracked_companies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),

        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE"
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "manager_id",
            "company_id",
            name="uq_manager_company_tracking"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("tracked_companies")