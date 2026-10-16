"""document version history (additive). Every existing document becomes version 1 of itself.

Adds document_versions, documents.current_version_id, document_chunks.version_id and processing_jobs.version_id, then
backfills them. No table is dropped and no existing column or row is removed or rewritten except the new NULLable
pointers being filled in. Files on disk are only read (to compute the SHA-256 of version 1), never moved.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-17 09:00:00
"""
import hashlib
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sha256(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(Path(path), 'rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None  # the file is missing: the version still exists, only its checksum is unknown


def upgrade() -> None:
    op.create_table(
        'document_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=True),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('change_note', sa.String(length=500), nullable=True),
        sa.Column('restored_from_version_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['restored_from_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'version_number', name='uq_document_versions_number'),
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])

    op.add_column('documents', sa.Column('current_version_id', sa.Integer(), nullable=True))
    op.create_index('ix_documents_current_version_id', 'documents', ['current_version_id'])
    op.create_foreign_key('fk_documents_current_version', 'documents', 'document_versions', ['current_version_id'], ['id'], ondelete='SET NULL')
    op.add_column('document_chunks', sa.Column('version_id', sa.Integer(), nullable=True))
    op.create_index('ix_document_chunks_version_id', 'document_chunks', ['version_id'])
    op.create_foreign_key('fk_document_chunks_version', 'document_chunks', 'document_versions', ['version_id'], ['id'], ondelete='CASCADE')
    op.add_column('processing_jobs', sa.Column('version_id', sa.Integer(), nullable=True))
    op.create_index('ix_processing_jobs_version_id', 'processing_jobs', ['version_id'])
    op.create_foreign_key('fk_processing_jobs_version', 'processing_jobs', 'document_versions', ['version_id'], ['id'], ondelete='CASCADE')

    # ---- backfill: each existing document becomes its own version 1 (same id stays on the document)
    conn = op.get_bind()
    docs = conn.execute(sa.text(
        'SELECT id, user_id, original_filename, storage_path, file_size, mime_type, processing_status, processing_error, total_pages, created_at FROM documents'
    )).mappings().all()
    for d in docs:
        conn.execute(
            sa.text(
                'INSERT INTO document_versions (document_id, version_number, original_filename, storage_path, file_size, mime_type, checksum_sha256, '
                'total_pages, processing_status, processing_error, created_by, created_at) '
                'VALUES (:document_id, 1, :name, :path, :size, :mime, :sum, :pages, :status, :error, :user, :created)'
            ),
            dict(document_id=d['id'], name=d['original_filename'], path=d['storage_path'], size=d['file_size'], mime=d['mime_type'],
                 sum=_sha256(d['storage_path']), pages=d['total_pages'], status=d['processing_status'], error=d['processing_error'],
                 user=d['user_id'], created=d['created_at']),
        )
    conn.execute(sa.text('UPDATE documents d JOIN document_versions v ON v.document_id = d.id AND v.version_number = 1 SET d.current_version_id = v.id'))
    conn.execute(sa.text('UPDATE document_chunks c JOIN document_versions v ON v.document_id = c.document_id AND v.version_number = 1 SET c.version_id = v.id'))
    conn.execute(sa.text('UPDATE processing_jobs j JOIN document_versions v ON v.document_id = j.document_id AND v.version_number = 1 SET j.version_id = v.id'))


def downgrade() -> None:
    # documents.storage_path/file_size/total_pages always mirror the current version, so the pre-versioning schema keeps
    # working. Older versions' rows are dropped with the table; their files stay on disk untouched.
    # Passages of non-current versions would be indistinguishable from current ones in the old schema, so they are removed
    # (the files and the current version's passages are kept; vectors of removed chunks become inert orphans).
    op.get_bind().execute(sa.text('DELETE c FROM document_chunks c JOIN documents d ON d.id = c.document_id WHERE c.version_id IS NOT NULL AND (d.current_version_id IS NULL OR c.version_id <> d.current_version_id)'))
    op.drop_constraint('fk_processing_jobs_version', 'processing_jobs', type_='foreignkey')
    op.drop_index('ix_processing_jobs_version_id', table_name='processing_jobs')
    op.drop_column('processing_jobs', 'version_id')
    op.drop_constraint('fk_document_chunks_version', 'document_chunks', type_='foreignkey')
    op.drop_index('ix_document_chunks_version_id', table_name='document_chunks')
    op.drop_column('document_chunks', 'version_id')
    op.drop_constraint('fk_documents_current_version', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_current_version_id', table_name='documents')
    op.drop_column('documents', 'current_version_id')
    op.drop_table('document_versions')
