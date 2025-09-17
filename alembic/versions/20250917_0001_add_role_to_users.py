"""add_role_to_users

Revision ID: 20250917_0001
Revises: 20250915_0001
Create Date: 2025-09-17 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250917_0001"
down_revision = "20250915_0001"
branch_labels = None
depends_on = None


def upgrade():
    """Add role column to users table."""
    # Add role column with default 'user' for existing users
    op.add_column(
        "users",
        sa.Column("role", sa.Enum("user", "admin", name="userrole"), nullable=True),
    )

    # Update existing users to have 'user' role
    op.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL"))

    # Make the column non-nullable after updating existing records
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("user", "admin", name="userrole"),
        nullable=False,
        server_default="user",
    )


def downgrade():
    """Remove role column from users table."""
    op.drop_column("users", "role")
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS userrole")
