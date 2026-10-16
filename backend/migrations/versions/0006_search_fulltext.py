"""FULLTEXT index on document_chunks.extracted_text for keyword search (index only; no data changes)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16 18:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ft_chunks_text', 'document_chunks', ['extracted_text'], mysql_prefix='FULLTEXT')


def downgrade() -> None:
    op.drop_index('ft_chunks_text', table_name='document_chunks')
