"""Create comprehensive devotee model and migrate from users

Revision ID: 20250921_0001
Revises: 20250917_0003
Create Date: 2025-09-21

This migration creates a new comprehensive devotee model with all ISKCON-specific
fields and migrates existing user data. It includes proper indexing for performance
optimization for 100K users.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250921_0001"
down_revision: str | None = "20250917_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create devotees table and migrate from users table."""

    # Create the devotees table with all comprehensive fields
    op.create_table(
        "devotees",
        # Primary key
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        # Authentication (consistent with existing system)
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        # Personal Information
        sa.Column("legal_name", sa.String(length=127), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.Enum("M", "F", name="gender"), nullable=False),
        sa.Column(
            "marital_status",
            sa.Enum(
                "SINGLE",
                "MARRIED",
                "DIVORCED",
                "WIDOWED",
                "SEPARATED",
                "OTHERS",
                name="maritalstatus",
            ),
            nullable=False,
        ),
        # Contact Information
        sa.Column("country_code", sa.String(length=5), nullable=False),
        sa.Column("mobile_number", sa.String(length=15), nullable=False),
        sa.Column("national_id", sa.String(length=50), nullable=True),
        # Family Information
        sa.Column("father_name", sa.String(length=127), nullable=False),
        sa.Column("mother_name", sa.String(length=127), nullable=False),
        sa.Column("spouse_name", sa.String(length=127), nullable=True),
        sa.Column("date_of_marriage", sa.Date(), nullable=True),
        sa.Column("children", mysql.JSON(), nullable=True),
        # Location Information
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state_province", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        # ISKCON Spiritual Information
        sa.Column(
            "initiation_status",
            sa.Enum("ASPIRING", "HARINAM", "BRAHMIN", name="initiationstatus"),
            nullable=True,
            default="ASPIRING",
        ),
        sa.Column("spiritual_master", sa.String(length=255), nullable=True),
        sa.Column("initiation_date", sa.Date(), nullable=True),
        sa.Column("initiation_place", sa.String(length=127), nullable=True),
        sa.Column("spiritual_guide", sa.String(length=127), nullable=True),
        # ISKCON Journey
        sa.Column("when_were_you_introduced_to_iskcon", sa.Date(), nullable=True),
        sa.Column(
            "who_introduced_you_to_iskcon",
            sa.String(length=127),
            nullable=True,
        ),
        sa.Column(
            "which_iskcon_center_you_first_connected_to",
            sa.String(length=127),
            nullable=True,
        ),
        # Chanting Practice
        sa.Column(
            "chanting_number_of_rounds",
            sa.Integer(),
            nullable=True,
            default=16,
        ),
        sa.Column("chanting_16_rounds_since", sa.Date(), nullable=True),
        # Devotional Education
        sa.Column("devotional_courses", sa.Text(), nullable=True),
        # System Fields
        sa.Column(
            "role",
            sa.Enum("USER", "ADMIN", name="userrole"),
            nullable=False,
            default="USER",
        ),
        sa.Column("password_reset_token", sa.String(length=255), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create performance optimization indexes
    with op.batch_alter_table("devotees") as batch_op:
        batch_op.create_index("idx_city_country", ["city", "country"])
        batch_op.create_index("idx_location_search", ["country", "state_province", "city"])
        batch_op.create_index("idx_spiritual_info", ["initiation_status", "spiritual_master"])
        batch_op.create_index("idx_name_search", ["legal_name"])
        batch_op.create_index("idx_mobile_search", ["country_code", "mobile_number"])
        batch_op.create_index("ix_devotees_city", ["city"])
        batch_op.create_index("ix_devotees_country", ["country"])
        batch_op.create_index("ix_devotees_initiation_status", ["initiation_status"])
        batch_op.create_index("ix_devotees_spiritual_master", ["spiritual_master"])

    # Migrate existing data from users table to devotees table
    # This is a data migration that maps existing user fields to devotee fields
    connection = op.get_bind()

    # Check if users table exists and has data
    result = connection.execute(sa.text("SHOW TABLES LIKE 'users'")).fetchone()
    if result:
        # Migrate users to devotees with default values for new fields
        migration_query = sa.text(
            """
            INSERT INTO devotees (
                email,
                password_hash,
                legal_name,
                date_of_birth,
                gender,
                marital_status,
                country_code,
                mobile_number,
                father_name,
                mother_name,
                chanting_number_of_rounds,
                role,
                password_reset_token,
                password_reset_expires,
                created_at,
                updated_at
            )
            SELECT
                email,
                password_hash,
                COALESCE(name, 'Name Required') as legal_name,
                '1990-01-01' as date_of_birth,  -- Default DOB, users will need to update
                'M' as gender,  -- Default gender, users will need to update
                'SINGLE' as marital_status,  -- Default marital status
                '91' as country_code,  -- Default to India
                '0000000000' as mobile_number,  -- Default placeholder
                'Father Name Required' as father_name,  -- Default placeholder
                'Mother Name Required' as mother_name,  -- Default placeholder
                COALESCE(chanting_rounds, 16) as chanting_number_of_rounds,
                role,
                password_reset_token,
                password_reset_expires,
                created_at,
                updated_at
            FROM users
        """
        )

        try:
            connection.execute(migration_query)
            connection.commit()
        except Exception as e:
            print(f"Warning: Could not migrate existing users data: {e}")
            # Continue with migration even if data migration fails


def downgrade() -> None:
    """Drop devotees table and restore users table functionality."""

    # Drop all indexes first
    with op.batch_alter_table("devotees", schema=None) as batch_op:
        batch_op.drop_index("idx_mobile_search")
        batch_op.drop_index("idx_name_search")
        batch_op.drop_index("idx_spiritual_info")
        batch_op.drop_index("idx_location_search")
        batch_op.drop_index("idx_city_country")
        batch_op.drop_index("ix_devotees_spiritual_master")
        batch_op.drop_index("ix_devotees_initiation_status")
        batch_op.drop_index("ix_devotees_country")
        batch_op.drop_index("ix_devotees_city")

    # Drop the devotees table
    op.drop_table("devotees")

    # Drop the new enums
    op.execute("DROP TYPE IF EXISTS initiationstatus")
    op.execute("DROP TYPE IF EXISTS maritalstatus")
    op.execute("DROP TYPE IF EXISTS gender")
