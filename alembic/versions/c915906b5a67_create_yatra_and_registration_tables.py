"""create_yatra_and_registration_tables

Revision ID: c915906b5a67
Revises: ca58fdff23ec
Create Date: 2025-11-26 12:07:34.202516

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'c915906b5a67'
down_revision = 'ca58fdff23ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create yatras table
    op.create_table(
        'yatras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('destination', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('registration_start_date', sa.Date(), nullable=False),
        sa.Column('registration_deadline', sa.Date(), nullable=False),
        sa.Column('price_per_person', sa.Integer(), nullable=False),
        sa.Column('child_discount_percentage', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('itinerary', mysql.JSON(), nullable=True),
        sa.Column('inclusions', sa.Text(), nullable=True),
        sa.Column('exclusions', sa.Text(), nullable=True),
        sa.Column('important_notes', sa.Text(), nullable=True),
        sa.Column('terms_and_conditions', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'UPCOMING', 'REGISTRATION_CLOSED', 'ONGOING', 'COMPLETED', 'CANCELLED', name='yatrastatus'), nullable=True, server_default='DRAFT'),
        sa.Column('is_featured', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['devotees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_yatra_registration_open', 'yatras', ['status', 'registration_deadline'], unique=False)
    op.create_index('idx_yatra_status_dates', 'yatras', ['status', 'start_date'], unique=False)
    op.create_index(op.f('ix_yatras_id'), 'yatras', ['id'], unique=False)
    op.create_index(op.f('ix_yatras_name'), 'yatras', ['name'], unique=False)
    op.create_index(op.f('ix_yatras_registration_deadline'), 'yatras', ['registration_deadline'], unique=False)
    op.create_index(op.f('ix_yatras_slug'), 'yatras', ['slug'], unique=True)
    op.create_index(op.f('ix_yatras_start_date'), 'yatras', ['start_date'], unique=False)
    op.create_index(op.f('ix_yatras_status'), 'yatras', ['status'], unique=False)

    # Create yatra_registrations table
    op.create_table(
        'yatra_registrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_number', sa.String(length=50), nullable=False),
        sa.Column('yatra_id', sa.Integer(), nullable=False),
        sa.Column('devotee_id', sa.Integer(), nullable=False),
        sa.Column('arrival_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('departure_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arrival_mode', sa.String(length=50), nullable=True),
        sa.Column('departure_mode', sa.String(length=50), nullable=True),
        sa.Column('room_preference', sa.Enum('SINGLE', 'DOUBLE_SHARING', 'TRIPLE_SHARING', 'QUAD_SHARING', 'DORMITORY', name='roompreference'), nullable=False),
        sa.Column('ac_preference', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('floor_preference', sa.String(length=50), nullable=True),
        sa.Column('special_room_requests', sa.Text(), nullable=True),
        sa.Column('number_of_members', sa.Integer(), nullable=False),
        sa.Column('accompanying_members', mysql.JSON(), nullable=True),
        sa.Column('total_amount', sa.Integer(), nullable=False),
        sa.Column('payment_screenshot_path', sa.String(length=512), nullable=True),
        sa.Column('payment_reference', sa.String(length=100), nullable=True),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'PAYMENT_SUBMITTED', 'PAYMENT_VERIFIED', 'CONFIRMED', 'CANCELLED_BY_USER', 'CANCELLED_BY_ADMIN', 'COMPLETED', name='registrationstatus'), nullable=True, server_default='PENDING'),
        sa.Column('status_history', mysql.JSON(), nullable=True),
        sa.Column('admin_remarks', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_by', sa.Integer(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_remarks', sa.Text(), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=127), nullable=True),
        sa.Column('emergency_contact_number', sa.String(length=20), nullable=True),
        sa.Column('dietary_requirements', sa.Text(), nullable=True),
        sa.Column('medical_conditions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['confirmed_by'], ['devotees.id'], ),
        sa.ForeignKeyConstraint(['devotee_id'], ['devotees.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['devotees.id'], ),
        sa.ForeignKeyConstraint(['yatra_id'], ['yatras.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registration_number')
    )
    op.create_index('idx_reg_devotee_status', 'yatra_registrations', ['devotee_id', 'status'], unique=False)
    op.create_index('idx_reg_number', 'yatra_registrations', ['registration_number'], unique=False)
    op.create_index('idx_reg_status_yatra', 'yatra_registrations', ['status', 'yatra_id'], unique=False)
    op.create_index('idx_reg_yatra_devotee', 'yatra_registrations', ['yatra_id', 'devotee_id'], unique=False)
    op.create_index(op.f('ix_yatra_registrations_devotee_id'), 'yatra_registrations', ['devotee_id'], unique=False)
    op.create_index(op.f('ix_yatra_registrations_id'), 'yatra_registrations', ['id'], unique=False)
    op.create_index(op.f('ix_yatra_registrations_registration_number'), 'yatra_registrations', ['registration_number'], unique=True)
    op.create_index(op.f('ix_yatra_registrations_status'), 'yatra_registrations', ['status'], unique=False)
    op.create_index(op.f('ix_yatra_registrations_yatra_id'), 'yatra_registrations', ['yatra_id'], unique=False)


def downgrade() -> None:
    # Drop yatra_registrations table
    op.drop_index(op.f('ix_yatra_registrations_yatra_id'), table_name='yatra_registrations')
    op.drop_index(op.f('ix_yatra_registrations_status'), table_name='yatra_registrations')
    op.drop_index(op.f('ix_yatra_registrations_registration_number'), table_name='yatra_registrations')
    op.drop_index(op.f('ix_yatra_registrations_id'), table_name='yatra_registrations')
    op.drop_index(op.f('ix_yatra_registrations_devotee_id'), table_name='yatra_registrations')
    op.drop_index('idx_reg_yatra_devotee', table_name='yatra_registrations')
    op.drop_index('idx_reg_status_yatra', table_name='yatra_registrations')
    op.drop_index('idx_reg_number', table_name='yatra_registrations')
    op.drop_index('idx_reg_devotee_status', table_name='yatra_registrations')
    op.drop_table('yatra_registrations')

    # Drop yatras table
    op.drop_index(op.f('ix_yatras_status'), table_name='yatras')
    op.drop_index(op.f('ix_yatras_start_date'), table_name='yatras')
    op.drop_index(op.f('ix_yatras_slug'), table_name='yatras')
    op.drop_index(op.f('ix_yatras_registration_deadline'), table_name='yatras')
    op.drop_index(op.f('ix_yatras_name'), table_name='yatras')
    op.drop_index(op.f('ix_yatras_id'), table_name='yatras')
    op.drop_index('idx_yatra_status_dates', table_name='yatras')
    op.drop_index('idx_yatra_registration_open', table_name='yatras')
    op.drop_table('yatras')
