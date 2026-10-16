"""persistent job queue columns on processing_jobs

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 10:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('processing_jobs', sa.Column('stage', sa.String(length=30), nullable=True))
    op.add_column('processing_jobs', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('processing_jobs', sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('processing_jobs', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('processing_jobs', sa.Column('next_run_at', sa.DateTime(), nullable=True))
    op.add_column('processing_jobs', sa.Column('locked_by', sa.String(length=64), nullable=True))
    op.add_column('processing_jobs', sa.Column('heartbeat_at', sa.DateTime(), nullable=True))
    op.add_column('processing_jobs', sa.Column('active_key', sa.Integer(), nullable=True))
    op.add_column('processing_jobs', sa.Column('error_code', sa.String(length=50), nullable=True))
    op.add_column('processing_jobs', sa.Column('error_detail', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_processing_jobs_active_key', 'processing_jobs', ['active_key'])
    op.create_index('ix_processing_jobs_queue', 'processing_jobs', ['status', 'next_run_at'])

    # Keep existing records meaningful under the new vocabulary (queued / processing / completed / failed).
    op.execute("UPDATE processing_jobs SET status='completed', progress=100 WHERE status='ready'")
    # Jobs that were still in flight when the old in-process runner stopped are re-queued so the worker finishes them.
    op.execute(
        "UPDATE processing_jobs j "
        "JOIN (SELECT MAX(id) AS mid FROM processing_jobs GROUP BY document_id) m ON j.id = m.mid "
        "JOIN documents d ON d.id = j.document_id "
        "SET j.status='queued', j.active_key=j.document_id "
        "WHERE j.status='processing' AND d.processing_status IN ('uploaded','processing')"
    )
    op.execute("UPDATE processing_jobs SET status='failed', error_message='Interrupted before the queue existed.' WHERE status='processing'")
    op.execute("UPDATE documents SET processing_status='queued' WHERE processing_status IN ('uploaded','processing')")


def downgrade() -> None:
    op.execute("UPDATE documents SET processing_status='processing' WHERE processing_status='queued'")
    op.execute("UPDATE processing_jobs SET status='processing' WHERE status='queued'")
    op.execute("UPDATE processing_jobs SET status='ready' WHERE status='completed'")
    op.drop_index('ix_processing_jobs_queue', table_name='processing_jobs')
    op.drop_constraint('uq_processing_jobs_active_key', 'processing_jobs', type_='unique')
    for col in ('error_detail', 'error_code', 'active_key', 'heartbeat_at', 'locked_by', 'next_run_at', 'max_attempts', 'attempts', 'progress', 'stage'):
        op.drop_column('processing_jobs', col)

