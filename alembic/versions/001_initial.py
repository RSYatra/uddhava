"""Initial migration: create devotees and family_members tables

Revision ID: 001_initial
Revises:
Create Date: 2026-01-25 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables."""
    # Create devotees table
    op.create_table(
        "devotees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(127), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("verification_token", sa.String(255), nullable=True),
        sa.Column(
            "verification_expires",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("password_reset_token", sa.String(255), nullable=True),
        sa.Column(
            "password_reset_expires",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="USER"),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devotees_email", "devotees", ["email"])
    op.create_index("ix_devotees_id", "devotees", ["id"])

    # Create family_members table
    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("devotee_id", sa.Integer(), nullable=False),
        sa.Column("legal_name", sa.String(127), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(1), nullable=True),
        sa.Column("mobile_number", sa.String(15), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("relationship", sa.String(50), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["devotee_id"],
            ["devotees.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_family_members_devotee_id",
        "family_members",
        ["devotee_id"],
    )
    op.create_index("ix_family_members_id", "family_members", ["id"])


def downgrade() -> None:
    """Drop tables."""
    op.drop_table("family_members")
    op.drop_table("devotees")
