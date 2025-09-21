"""add_email_verification_fields

Revision ID: 20250122_0001
Revises: e6a131e6945e
Create Date: 2025-01-22 15:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250122_0001"
down_revision = "e6a131e6945e"
branch_labels = None
depends_on = None


def upgrade():
    """Add email verification fields to users and devotees tables."""

    # Add email verification fields to users table
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, default=False),
    )

    op.add_column(
        "users",
        sa.Column("verification_token", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("verification_expires", sa.DateTime(timezone=True), nullable=True),
    )

    # Add email verification fields to devotees table
    op.add_column(
        "devotees",
        sa.Column("email_verified", sa.Boolean(), nullable=False, default=False),
    )

    op.add_column(
        "devotees",
        sa.Column("verification_token", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "devotees",
        sa.Column("verification_expires", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes on verification tokens for faster lookups
    op.create_index(
        op.f("ix_users_verification_token"),
        "users",
        ["verification_token"],
        unique=False,
    )

    op.create_index(
        op.f("ix_devotees_verification_token"),
        "devotees",
        ["verification_token"],
        unique=False,
    )


def downgrade():
    """Remove email verification fields from users and devotees tables."""

    # Drop indexes
    op.drop_index(op.f("ix_users_verification_token"), table_name="users")
    op.drop_index(op.f("ix_devotees_verification_token"), table_name="devotees")

    # Drop columns from users table
    op.drop_column("users", "verification_expires")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "email_verified")

    # Drop columns from devotees table
    op.drop_column("devotees", "verification_expires")
    op.drop_column("devotees", "verification_token")
    op.drop_column("devotees", "email_verified")
