"""Fix enum data values for gender and marital_status

Revision ID: e6a131e6945e
Revises: 20250921_0001
Create Date: 2025-09-21 17:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6a131e6945e"
down_revision: str | None = "20250921_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fix enum values in devotees table."""

    # Fix gender enum values
    op.execute("UPDATE devotees SET gender = 'MALE' WHERE gender = 'M'")
    op.execute("UPDATE devotees SET gender = 'FEMALE' WHERE gender = 'F'")

    # Fix marital status enum values if needed
    op.execute("UPDATE devotees SET marital_status = 'SINGLE' WHERE marital_status = 'SINGLE'")
    op.execute("UPDATE devotees SET marital_status = 'MARRIED' WHERE marital_status = 'MARRIED'")
    op.execute("UPDATE devotees SET marital_status = 'DIVORCED' WHERE marital_status = 'DIVORCED'")
    op.execute("UPDATE devotees SET marital_status = 'WIDOWED' WHERE marital_status = 'WIDOWED'")


def downgrade() -> None:
    """Revert enum values in devotees table."""

    # Revert gender enum values
    op.execute("UPDATE devotees SET gender = 'M' WHERE gender = 'MALE'")
    op.execute("UPDATE devotees SET gender = 'F' WHERE gender = 'FEMALE'")
