"""add operation_batches and batch relation

Revision ID: 7c31c841308f
Revises: 5d1b36177f47
Create Date: 2026-03-02 23:47:56.571975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7c31c841308f'
down_revision: Union[str, Sequence[str], None] = '5d1b36177f47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operation_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('total_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('inserted_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_operation_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['company_id'],
            ['companies.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    op.add_column(
        'bank_operations',
        sa.Column(
            'import_batch_id',
            postgresql.UUID(as_uuid=True),
            nullable=False
        )
    )

    op.create_foreign_key(
        'fk_bank_operations_batch',
        'bank_operations',
        'operation_batches',
        ['import_batch_id'],
        ['id'],
        ondelete='CASCADE'
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_constraint(
        'fk_bank_operations_batch',
        'bank_operations',
        type_='foreignkey'
    )
    op.drop_column('bank_operations', 'import_batch_id')
    op.drop_table('operation_batches')
    # ### end Alembic commands ###
