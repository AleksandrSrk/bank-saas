"""sync + company mapping

Revision ID: 61b4fd308352
Revises: 2571777c8159
Create Date: 2026-03-17 18:35:40.292554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '61b4fd308352'
down_revision: Union[str, Sequence[str], None] = '2571777c8159'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    
    op.create_foreign_key(
        "fk_bank_accounts_legal_entity",
        "bank_accounts",
        "legal_entities",
        ["legal_entity_id"],
        ["id"]
    )

    op.create_foreign_key(
        "fk_bank_operations_legal_entity",
        "bank_operations",
        "legal_entities",
        ["legal_entity_id"],
        ["id"]
    )

    op.alter_column(
        "bank_operations",
        "company_id",
        existing_type=sa.UUID(),
        nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    pass