"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('github_id', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('github_id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_github_id', 'users', ['github_id'], unique=True)

    # Repositories table
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.Column('default_branch', sa.String(100), server_default='main', nullable=False),
        sa.Column('language_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_files', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_lines', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('analysis_progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('complexity_score', sa.Numeric(4, 2), nullable=True),
        sa.Column('architecture_type', sa.String(50), server_default='Unknown', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_repositories_user_id', 'repositories', ['user_id'])
    op.create_index('ix_repositories_status', 'repositories', ['status'])
    op.create_index('ix_repositories_user_id_created_at', 'repositories', ['user_id', 'created_at'])

    # Files table
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.String(1000), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('extension', sa.String(50), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('line_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('complexity_score', sa.Numeric(4, 2), nullable=True),
        sa.Column('is_entry_point', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_test_file', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'path', name='uq_file_repo_path'),
    )
    op.create_index('ix_files_repository_id', 'files', ['repository_id'])
    op.create_index('ix_files_repo_language', 'files', ['repository_id', 'language'])

    # Symbols table
    op.create_table(
        'symbols',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('qualified_name', sa.String(500), nullable=True),
        sa.Column('symbol_type', sa.String(50), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('docstring', sa.Text(), nullable=True),
        sa.Column('is_exported', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_dead_code', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('call_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('complexity_score', sa.Numeric(4, 2), nullable=True),
        sa.Column('embedding_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_symbols_file_id', 'symbols', ['file_id'])
    op.create_index('ix_symbols_repository_id', 'symbols', ['repository_id'])
    op.create_index('ix_symbols_symbol_type', 'symbols', ['symbol_type'])
    op.create_index('ix_symbols_qualified_name', 'symbols', ['qualified_name'])
    op.create_index('ix_symbols_repo_type', 'symbols', ['repository_id', 'symbol_type'])
    op.create_index('ix_symbols_is_dead_code', 'symbols', ['is_dead_code'])

    # Relationships table
    op.create_table(
        'relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_symbol_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_symbol_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Integer(), server_default='1', nullable=False),
        sa.Column('is_dynamic', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_symbol_id'], ['symbols.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_symbol_id'], ['symbols.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_relationships_repository_id', 'relationships', ['repository_id'])
    op.create_index('ix_relationships_source_symbol_id', 'relationships', ['source_symbol_id'])
    op.create_index('ix_relationships_target_symbol_id', 'relationships', ['target_symbol_id'])
    op.create_index('ix_relationships_source_target', 'relationships', ['source_symbol_id', 'target_symbol_id'])
    op.create_index('ix_relationships_repo_type', 'relationships', ['repository_id', 'relationship_type'])

    # Analysis Reports table
    op.create_table(
        'analysis_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analysis_reports_repository_id', 'analysis_reports', ['repository_id'])
    op.create_index('ix_analysis_reports_repo_type', 'analysis_reports', ['repository_id', 'report_type'])

    # Chat Messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_symbols', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_repository_id', 'chat_messages', ['repository_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_chat_messages_repo_created', 'chat_messages', ['repository_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('analysis_reports')
    op.drop_table('relationships')
    op.drop_table('symbols')
    op.drop_table('files')
    op.drop_table('repositories')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')