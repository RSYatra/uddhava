"""add_password_reset_fields

Revision ID: 20250917_0002
Revises: 20250917_0001
Create Date: 2025-09-17 15:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250917_0002"
down_revision = "20250917_0001"
branch_labels = None
depends_on = None


def upgrade():
    """Add password reset fields to users table."""
    # Add password_reset_token column
    op.add_column(
        "users",
        sa.Column("password_reset_token", sa.String(length=255), nullable=True),
    )

    # Add password_reset_expires column
    op.add_column(
        "users",
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
    )

    # Create index on password_reset_token for faster lookups
    op.create_index(
        op.f("ix_users_password_reset_token"),
        "users",
        ["password_reset_token"],
        unique=False,
    )


def downgrade():
    """Remove password reset fields from users table."""
    # Drop index
    op.drop_index(op.f("ix_users_password_reset_token"), table_name="users")

    # Drop columns
    op.drop_column("users", "password_reset_expires")
    op.drop_column("users", "password_reset_token")
