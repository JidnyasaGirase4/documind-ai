"""collections, categories and tags (additive: no existing table or row is dropped or rewritten)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16 10:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('icon', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'name', name='uq_collections_owner_name'),
    )
    op.create_index('ix_collections_owner_id', 'collections', ['owner_id'])

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'name', name='uq_categories_owner_name'),
    )
    op.create_index('ix_categories_owner_id', 'categories', ['owner_id'])

    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'name', name='uq_tags_owner_name'),
    )
    op.create_index('ix_tags_owner_id', 'tags', ['owner_id'])

    op.create_table(
        'collection_documents',
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('collection_id', 'document_id'),
    )
    op.create_index('ix_collection_documents_document', 'collection_documents', ['document_id'])

    op.create_table(
        'document_tags',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'tag_id'),
    )
    op.create_index('ix_document_tags_tag', 'document_tags', ['tag_id'])

    # Nullable column: every existing document keeps working and simply has no category.
    op.add_column('documents', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_index('ix_documents_category_id', 'documents', ['category_id'])
    op.create_foreign_key('fk_documents_category', 'documents', 'categories', ['category_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_documents_category', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_category_id', table_name='documents')
    op.drop_column('documents', 'category_id')
    op.drop_table('document_tags')
    op.drop_table('collection_documents')
    op.drop_table('tags')
    op.drop_table('categories')
    op.drop_table('collections')
