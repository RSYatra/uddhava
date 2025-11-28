"""clean_slate_yatra_redesign

Revision ID: da97198bd197
Revises: 4f8325c2d1be
Create Date: 2025-11-28 17:09:02.508975

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'da97198bd197'
down_revision = '4f8325c2d1be'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old tables if they exist (in correct order respecting foreign keys)
    # Use raw SQL with IF EXISTS to handle cases where tables don't exist yet
    op.execute('DROP TABLE IF EXISTS yatra_members')
    op.execute('DROP TABLE IF EXISTS yatra_registrations')
    op.execute('DROP TABLE IF EXISTS yatra_payment_options')
    op.execute('DROP TABLE IF EXISTS pricing_template_details')
    op.execute('DROP TABLE IF EXISTS yatras')
    op.execute('DROP TABLE IF EXISTS payment_options')
    op.execute('DROP TABLE IF EXISTS pricing_templates')

    # Create new yatras table (simplified)
    op.create_table(
        'yatras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('destination', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('registration_deadline', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('itinerary', sa.Text(), nullable=True),
        sa.Column('terms_and_conditions', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create new room_categories table
    op.create_table(
        'room_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yatra_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('price_per_person', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['yatra_id'], ['yatras.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('yatra_id', 'name', name='unique_category_per_yatra')
    )

    # Create new payment_options table
    op.create_table(
        'payment_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('method', sa.Enum('UPI', 'BANK_TRANSFER', 'QR_CODE', 'CASH', 'CHEQUE', name='paymentmethod'), nullable=False),
        sa.Column('upi_id', sa.String(length=100), nullable=True),
        sa.Column('account_holder', sa.String(length=255), nullable=True),
        sa.Column('account_number', sa.String(length=50), nullable=True),
        sa.Column('ifsc_code', sa.String(length=20), nullable=True),
        sa.Column('bank_name', sa.String(length=255), nullable=True),
        sa.Column('branch', sa.String(length=255), nullable=True),
        sa.Column('qr_code_url', sa.String(length=500), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create new yatra_payment_options table (simplified, no display_order)
    op.create_table(
        'yatra_payment_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yatra_id', sa.Integer(), nullable=False),
        sa.Column('payment_option_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['yatra_id'], ['yatras.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_option_id'], ['payment_options.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('yatra_id', 'payment_option_id', name='unique_payment_per_yatra')
    )

    # Create new yatra_registrations table (simplified, new group_id format)
    op.create_table(
        'yatra_registrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yatra_id', sa.Integer(), nullable=False),
        sa.Column('devotee_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.String(length=50), nullable=False),
        sa.Column('is_group_lead', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('payment_option_id', sa.Integer(), nullable=False),
        sa.Column('payment_amount', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('payment_status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='paymentstatus'), nullable=False, server_default='PENDING'),
        sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED', name='registrationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['yatra_id'], ['yatras.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['devotee_id'], ['devotees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_option_id'], ['payment_options.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_yatra_registrations_group_id', 'group_id'),
        sa.Index('idx_yatra_registrations_yatra_id', 'yatra_id'),
        sa.Index('idx_yatra_registrations_devotee_id', 'devotee_id')
    )

    # Create new yatra_members table (simplified, room_category as VARCHAR)
    op.create_table(
        'yatra_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('devotee_id', sa.Integer(), nullable=True),
        sa.Column('legal_name', sa.String(length=127), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.Enum('M', 'F', name='gender'), nullable=False),
        sa.Column('room_category', sa.String(length=100), nullable=False),
        sa.Column('room_preference', sa.Enum('MALE_SHARING', 'FEMALE_SHARING', 'FAMILY', 'FAMILY_WITH_CHILDREN', name='roompreference'), nullable=False),
        sa.Column('is_primary_registrant', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('mobile_number', sa.String(length=15), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('dietary_requirements', sa.String(length=255), nullable=True),
        sa.Column('medical_conditions', sa.String(length=255), nullable=True),
        sa.Column('price_charged', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('arrival_datetime', sa.DateTime(), nullable=True),
        sa.Column('departure_datetime', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['registration_id'], ['yatra_registrations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['devotee_id'], ['devotees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_yatra_members_registration_id', 'registration_id'),
        sa.Index('idx_yatra_members_devotee_id', 'devotee_id')
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_table('yatra_members')
    op.drop_table('yatra_registrations')
    op.drop_table('yatra_payment_options')
    op.drop_table('room_categories')
    op.drop_table('payment_options')
    op.drop_table('yatras')

    # Note: Downgrade doesn't recreate old tables as this is a clean slate migration
    # If needed, old table structures would need to be recreated here
