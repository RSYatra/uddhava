"""Add password_hash field to users table

Revision ID: 20250914_2344_add_password_hash
Revises: 20250914_0001_baseline
Create Date: 2025-09-14 23:44:00.000000

"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250914_2344_add_password_hash"
down_revision = "20250914_0001"
branch_labels = None
depends_on = None


def upgrade():
    """Add password_hash column to users table"""
    # Add password_hash column with a default value for existing users
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )

    # Update existing users with a temporary password hash
    # In production, you'd want to handle this differently (e.g., force password reset)
    dummy_hash = "$2b$12$dummy.hash.for.existing.users.only"
    # nosec: B608 - Safe parameterized query for migration
    op.execute(
        text(
            "UPDATE users SET password_hash = :dummy_hash WHERE password_hash IS NULL"
        ),
        {"dummy_hash": dummy_hash},
    )

    # Make the column non-nullable after updating existing records
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade():
    """Remove password_hash column from users table"""
    op.drop_column("users", "password_hash")
