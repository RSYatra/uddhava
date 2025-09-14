"""baseline users table

Revision ID: 20250914_0001
Revises:
Create Date: 2025-09-14

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250914_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        # Table already exists (pre-Alembic adoption). Stamp only.
        return
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("chanting_rounds", sa.Integer(), nullable=False),
        sa.Column("photo", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
