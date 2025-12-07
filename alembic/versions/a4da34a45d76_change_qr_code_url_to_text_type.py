"""change qr_code_url to text type

Revision ID: a4da34a45d76
Revises: da97198bd197
Create Date: 2025-12-07 11:36:46.387822

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4da34a45d76'
down_revision = 'da97198bd197'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change qr_code_url from VARCHAR(500) to TEXT for unlimited length."""
    op.alter_column('payment_options', 'qr_code_url',
                    existing_type=sa.String(length=500),
                    type_=sa.Text(),
                    existing_nullable=True)


def downgrade() -> None:
    """Rollback: TEXT back to VARCHAR(500)."""
    op.alter_column('payment_options', 'qr_code_url',
                    existing_type=sa.Text(),
                    type_=sa.String(length=500),
                    existing_nullable=True)
