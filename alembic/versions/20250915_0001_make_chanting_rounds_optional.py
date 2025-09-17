"""make_chanting_rounds_optional

Revision ID: 20250915_0001
Revises: 20250914_2344
Create Date: 2025-09-15 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250915_0001"
down_revision = "20250914_2344_add_password_hash"
branch_labels = None
depends_on = None


def upgrade():
    """Make chanting_rounds column nullable and add default value."""
    # Modify the chanting_rounds column to be nullable with a default of 16
    op.alter_column(
        "users",
        "chanting_rounds",
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
        server_default="16",
    )


def downgrade():
    """Revert chanting_rounds column to be non-nullable."""
    # First, update any NULL values to have a default value
    op.execute("UPDATE users SET chanting_rounds = 16 WHERE chanting_rounds IS NULL")

    # Then make the column non-nullable again
    op.alter_column(
        "users",
        "chanting_rounds",
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
        server_default=None,
    )
