"""add_file_upload_fields_to_devotee

Revision ID: 07f90a5eaab3
Revises: 117d9e2d09f8
Create Date: 2025-10-10 16:32:17.972174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07f90a5eaab3'
down_revision = '117d9e2d09f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file upload fields to devotees table
    op.add_column('devotees', sa.Column('profile_photo_path', sa.String(length=512), nullable=True))
    op.add_column('devotees', sa.Column('uploaded_files', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove file upload fields from devotees table
    op.drop_column('devotees', 'uploaded_files')
    op.drop_column('devotees', 'profile_photo_path')
