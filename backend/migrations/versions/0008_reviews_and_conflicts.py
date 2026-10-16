"""content review schedules/history and potential-conflict reports (additive: new tables only)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-18 09:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('interval_days', sa.Integer(), nullable=True),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.Column('assigned_reviewer_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('in_review', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('in_review_started_by', sa.Integer(), nullable=True),
        sa.Column('in_review_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('last_reviewed_by', sa.Integer(), nullable=True),
        sa.Column('last_outcome', sa.String(length=30), nullable=True),
        sa.Column('last_reviewed_version_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['in_review_started_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['last_reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['last_reviewed_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', name='uq_document_reviews_document'),
    )
    op.create_index('ix_document_reviews_next', 'document_reviews', ['next_review_date'])
    op.create_index('ix_document_reviews_assigned_reviewer_id', 'document_reviews', ['assigned_reviewer_id'])

    op.create_table(
        'document_review_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False),
        sa.Column('outcome', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('previous_next_review_date', sa.Date(), nullable=True),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_review_history_document', 'document_review_history', ['document_id', 'reviewed_at'])
    op.create_index('ix_review_history_reviewed_at', 'document_review_history', ['reviewed_at'])

    op.create_table(
        'conflict_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('scope_document_id', sa.Integer(), nullable=True),
        sa.Column('scope_collection_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('passages_examined', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pairs_examined', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pairs_unparsed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pairs_compatible', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scope_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scope_collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conflict_reports_created_by', 'conflict_reports', ['created_by'])
    op.create_index('ix_conflict_reports_scope_document_id', 'conflict_reports', ['scope_document_id'])
    op.create_index('ix_conflict_reports_scope_collection_id', 'conflict_reports', ['scope_collection_id'])

    op.create_table(
        'document_conflicts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('pair_key', sa.String(length=40), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('conflict_type', sa.String(length=30), nullable=False),
        sa.Column('assessment', sa.String(length=20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('a_document_id', sa.Integer(), nullable=False),
        sa.Column('a_version_id', sa.Integer(), nullable=True),
        sa.Column('a_chunk_id', sa.Integer(), nullable=True),
        sa.Column('a_page', sa.Integer(), nullable=True),
        sa.Column('a_excerpt', sa.Text(), nullable=False),
        sa.Column('b_document_id', sa.Integer(), nullable=False),
        sa.Column('b_version_id', sa.Integer(), nullable=True),
        sa.Column('b_chunk_id', sa.Integer(), nullable=True),
        sa.Column('b_page', sa.Integer(), nullable=True),
        sa.Column('b_excerpt', sa.Text(), nullable=False),
        sa.Column('quotes_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('review_status', sa.String(length=20), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['conflict_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['a_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['a_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['a_chunk_id'], ['document_chunks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['b_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['b_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['b_chunk_id'], ['document_chunks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pair_key', name='uq_document_conflicts_pair'),
    )
    op.create_index('ix_document_conflicts_report_id', 'document_conflicts', ['report_id'])
    op.create_index('ix_document_conflicts_a_doc', 'document_conflicts', ['a_document_id'])
    op.create_index('ix_document_conflicts_b_doc', 'document_conflicts', ['b_document_id'])

    op.create_table(
        'conflict_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conflict_id', sa.Integer(), nullable=False),
        sa.Column('decided_by', sa.Integer(), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conflict_id'], ['document_conflicts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conflict_decisions_conflict_id', 'conflict_decisions', ['conflict_id'])


def downgrade() -> None:
    # Drops the tables created above. Documents, versions and every earlier table are untouched; review schedules, review
    # history, conflict reports and reviewer decisions recorded since the upgrade are lost.
    op.drop_table('conflict_decisions')
    op.drop_table('document_conflicts')
    op.drop_table('conflict_reports')
    op.drop_table('document_review_history')
    op.drop_table('document_reviews')
