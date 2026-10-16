"""answer feedback, query logs and RAG evaluation tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'message_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.String(length=10), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', name='uq_feedback_message_user'),
    )
    op.create_index('ix_message_feedback_message_id', 'message_feedback', ['message_id'])
    op.create_index('ix_feedback_user_created', 'message_feedback', ['user_id', 'created_at'])

    op.create_table(
        'query_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('outcome', sa.String(length=30), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('citation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_query_logs_user_created', 'query_logs', ['user_id', 'created_at'])

    op.create_table(
        'eval_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('dataset_name', sa.String(length=100), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=False),
        sa.Column('dataset_hash', sa.String(length=64), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=False),
        sa.Column('judge', sa.String(length=20), nullable=False),
        sa.Column('k', sa.Integer(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'eval_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answerable', sa.Boolean(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('relevant', sa.JSON(), nullable=True),
        sa.Column('retrieved', sa.JSON(), nullable=True),
        sa.Column('cited', sa.JSON(), nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(length=30), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('precision_at_k', sa.Float(), nullable=True),
        sa.Column('recall_at_k', sa.Float(), nullable=True),
        sa.Column('citation_correctness', sa.Float(), nullable=True),
        sa.Column('faithfulness', sa.Float(), nullable=True),
        sa.Column('faithfulness_method', sa.String(length=20), nullable=True),
        sa.Column('keyword_recall', sa.Float(), nullable=True),
        sa.Column('correct_abstention', sa.Boolean(), nullable=True),
        sa.Column('retrieval_ms', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_eval_results_run_id', 'eval_results', ['run_id'])


def downgrade() -> None:
    # Dropping a table also drops its indexes (MySQL refuses to drop an index a foreign key still needs).
    op.drop_table('eval_results')
    op.drop_table('eval_runs')
    op.drop_table('query_logs')
    op.drop_table('message_feedback')
