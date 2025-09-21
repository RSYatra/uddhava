"""remove_unnecessary_indexes

Revision ID: 20250917_0003
Revises: 20250917_0002
Create Date: 2025-09-17 19:15:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250917_0003"
down_revision = "20250917_0002"
branch_labels = None
depends_on = None


def upgrade():
    """Remove unnecessary indexes for better write performance."""
    # Drop index on password_reset_token (lookup done via JWT email, not token)
    # Note: ix_users_name doesn't exist in current database, so we skip it
    op.drop_index(op.f("ix_users_password_reset_token"), table_name="users")


def downgrade():
    """Recreate indexes if needed."""
    # Recreate password_reset_token index
    op.create_index(
        op.f("ix_users_password_reset_token"),
        "users",
        ["password_reset_token"],
        unique=False,
    )
