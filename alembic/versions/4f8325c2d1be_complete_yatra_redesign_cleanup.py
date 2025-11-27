"""complete_yatra_redesign_cleanup

Revision ID: 4f8325c2d1be
Revises: 9fdafadf3009
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4f8325c2d1be'
down_revision = '9fdafadf3009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Complete the cleanup of old yatra_registrations columns."""

    # Remove old columns from yatra_registrations that weren't removed in previous migration
    columns_to_drop = [
        'status_history',
        'medical_conditions',
        'dietary_requirements',
        'emergency_contact_number',
        'emergency_contact_name',
        'user_remarks',
        'accompanying_members',
        'number_of_members',
        'special_room_requests',
        'floor_preference',
        'ac_preference',
        'room_preference',
        'departure_mode',
        'arrival_mode',
        'departure_datetime',
        'arrival_datetime',
    ]

    for column in columns_to_drop:
        try:
            op.drop_column('yatra_registrations', column)
        except Exception:
            # Column might already be dropped
            pass


def downgrade() -> None:
    """Add back the old columns."""

    # Add back old columns (reverse of upgrade)
    op.add_column('yatra_registrations', sa.Column('arrival_datetime', sa.DateTime(timezone=True), nullable=True))
    op.add_column('yatra_registrations', sa.Column('departure_datetime', sa.DateTime(timezone=True), nullable=True))
    op.add_column('yatra_registrations', sa.Column('arrival_mode', sa.String(length=50), nullable=True))
    op.add_column('yatra_registrations', sa.Column('departure_mode', sa.String(length=50), nullable=True))
    op.add_column('yatra_registrations', sa.Column('room_preference', sa.Enum('SINGLE', 'DOUBLE_SHARING', 'TRIPLE_SHARING', 'QUAD_SHARING', 'DORMITORY', name='roompreference'), nullable=True))
    op.add_column('yatra_registrations', sa.Column('ac_preference', sa.Boolean(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('floor_preference', sa.String(length=50), nullable=True))
    op.add_column('yatra_registrations', sa.Column('special_room_requests', sa.Text(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('number_of_members', sa.Integer(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('accompanying_members', mysql.JSON(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('user_remarks', sa.Text(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('emergency_contact_name', sa.String(length=127), nullable=True))
    op.add_column('yatra_registrations', sa.Column('emergency_contact_number', sa.String(length=20), nullable=True))
    op.add_column('yatra_registrations', sa.Column('dietary_requirements', sa.Text(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('medical_conditions', sa.Text(), nullable=True))
    op.add_column('yatra_registrations', sa.Column('status_history', mysql.JSON(), nullable=True))
