"""update_marital_status_enum_values

Revision ID: ca58fdff23ec
Revises: 07f90a5eaab3
Create Date: 2025-11-09 16:18:52.052439

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ca58fdff23ec'
down_revision = '07f90a5eaab3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Update marital_status enum values from:
    SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED, OTHERS
    to:
    BACHELOR, GRHASTA, VANPRASTHA, SANYAS, DIVORCED, WIDOWED
    """
    # For MySQL, we need to recreate the enum with new values
    # Step 1: Modify column to support all old and new values temporarily
    op.execute("""
        ALTER TABLE devotees
        MODIFY COLUMN marital_status
        ENUM('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED', 'OTHERS',
             'BACHELOR', 'GRHASTA', 'VANPRASTHA', 'SANYAS')
    """)

    # Step 2: Migrate existing data to new values
    op.execute("UPDATE devotees SET marital_status = 'BACHELOR' WHERE marital_status = 'SINGLE'")
    op.execute("UPDATE devotees SET marital_status = 'GRHASTA' WHERE marital_status = 'MARRIED'")
    op.execute("UPDATE devotees SET marital_status = 'BACHELOR' WHERE marital_status = 'SEPARATED'")
    op.execute("UPDATE devotees SET marital_status = 'BACHELOR' WHERE marital_status = 'OTHERS'")

    # Step 3: Update column to only include new values
    op.execute("""
        ALTER TABLE devotees
        MODIFY COLUMN marital_status
        ENUM('BACHELOR', 'GRHASTA', 'VANPRASTHA', 'SANYAS', 'DIVORCED', 'WIDOWED')
    """)


def downgrade() -> None:
    """Revert to old marital status enum values."""
    # Step 1: Modify column to support all values
    op.execute("""
        ALTER TABLE devotees
        MODIFY COLUMN marital_status
        ENUM('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED', 'OTHERS',
             'BACHELOR', 'GRHASTA', 'VANPRASTHA', 'SANYAS')
    """)

    # Step 2: Migrate data back to old values
    op.execute("UPDATE devotees SET marital_status = 'SINGLE' WHERE marital_status = 'BACHELOR'")
    op.execute("UPDATE devotees SET marital_status = 'MARRIED' WHERE marital_status = 'GRHASTA'")
    op.execute("UPDATE devotees SET marital_status = 'SINGLE' WHERE marital_status = 'VANPRASTHA'")
    op.execute("UPDATE devotees SET marital_status = 'SINGLE' WHERE marital_status = 'SANYAS'")

    # Step 3: Update column to only include old values
    op.execute("""
        ALTER TABLE devotees
        MODIFY COLUMN marital_status
        ENUM('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'SEPARATED', 'OTHERS')
    """)
