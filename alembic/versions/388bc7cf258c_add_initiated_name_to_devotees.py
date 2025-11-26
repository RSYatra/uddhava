"""add_initiated_name_to_devotees

Revision ID: 388bc7cf258c
Revises: c915906b5a67
Create Date: 2025-11-26 23:13:52.259099

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '388bc7cf258c'
down_revision = 'c915906b5a67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add initiated_name column to devotees table."""
    op.add_column(
        'devotees',
        sa.Column(
            'initiated_name',
            sa.String(length=127),
            nullable=True,
            comment='Spiritual name given at initiation (Harinam or Brahmin)'
        )
    )


def downgrade() -> None:
    """Remove initiated_name column from devotees table."""
    op.drop_column('devotees', 'initiated_name')
