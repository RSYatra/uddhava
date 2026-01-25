"""Initial minimal migration: create devotees table for frontend.

This migration creates a minimal `devotees` table with fields required by
the frontend auth flow (legal_name, email, password_hash, email_verified,
verification token/expires, password reset token/expires, timestamps).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'devotees',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('email_verified', sa.Boolean, nullable=False, server_default=sa.text('0')),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('verification_expires', sa.DateTime, nullable=True),
        sa.Column('legal_name', sa.String(127), nullable=False),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table('devotees')
