"""redesign_yatra_system_with_reusable_templates

Revision ID: 9fdafadf3009
Revises: 388bc7cf258c
Create Date: 2025-11-27 14:36:57.502029

"""
import json
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '9fdafadf3009'
down_revision = '388bc7cf258c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade to new yatra system with reusable templates.

    This migration:
    1. Creates new tables for pricing templates and payment options
    2. Creates yatra_members table for individual member tracking
    3. Modifies yatras table to use pricing templates
    4. Modifies yatra_registrations table for group management
    5. Migrates existing data
    """

    # Step 1: No need to modify yatra status enum - it's already correct

    # Step 2: Create pricing_templates table
    op.create_table(
        'pricing_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=127), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_pricing_templates_id', 'pricing_templates', ['id'])
    op.create_index('ix_pricing_templates_is_active', 'pricing_templates', ['is_active'])

    # Step 3: Create pricing_template_details table
    op.create_table(
        'pricing_template_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('room_category', sa.Enum('SHARED_AC', 'SHARED_NON_AC', 'PRIVATE_AC', 'PRIVATE_NON_AC', 'FAMILY_AC', 'FAMILY_NON_AC', name='roomcategory'), nullable=False),
        sa.Column('price_per_person', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['pricing_templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'room_category', name='uq_template_room')
    )
    op.create_index('idx_template_pricing', 'pricing_template_details', ['template_id', 'room_category'])

    # Step 4: Create payment_options table
    op.create_table(
        'payment_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=127), nullable=False),
        sa.Column('bank_account_number', sa.String(length=50), nullable=True),
        sa.Column('ifsc_code', sa.String(length=20), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('branch_name', sa.String(length=100), nullable=True),
        sa.Column('account_holder_name', sa.String(length=127), nullable=True),
        sa.Column('account_type', sa.String(length=50), nullable=True),
        sa.Column('upi_id', sa.String(length=100), nullable=True),
        sa.Column('upi_phone_number', sa.String(length=20), nullable=True),
        sa.Column('qr_code_path', sa.String(length=512), nullable=True),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_payment_options_id', 'payment_options', ['id'])
    op.create_index('ix_payment_options_is_active', 'payment_options', ['is_active'])

    # Step 5: Create yatra_payment_options junction table
    op.create_table(
        'yatra_payment_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yatra_id', sa.Integer(), nullable=False),
        sa.Column('payment_option_id', sa.Integer(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['payment_option_id'], ['payment_options.id'], ),
        sa.ForeignKeyConstraint(['yatra_id'], ['yatras.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('yatra_id', 'payment_option_id', name='uq_yatra_payment')
    )
    op.create_index('idx_yatra_payment', 'yatra_payment_options', ['yatra_id'])

    # Step 6: Create yatra_members table
    op.create_table(
        'yatra_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('devotee_id', sa.Integer(), nullable=True),
        sa.Column('legal_name', sa.String(length=127), nullable=False),
        sa.Column('gender', sa.Enum('M', 'F', name='gender'), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('mobile_number', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('arrival_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('departure_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('room_category', sa.Enum('SHARED_AC', 'SHARED_NON_AC', 'PRIVATE_AC', 'PRIVATE_NON_AC', 'FAMILY_AC', 'FAMILY_NON_AC', name='roomcategory'), nullable=False),
        sa.Column('price_charged', sa.Integer(), nullable=False),
        sa.Column('is_free', sa.Boolean(), nullable=True),
        sa.Column('is_primary_registrant', sa.Boolean(), nullable=True),
        sa.Column('is_registered_user', sa.Boolean(), nullable=True),
        sa.Column('dietary_requirements', sa.String(length=255), nullable=True),
        sa.Column('medical_conditions', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['devotee_id'], ['devotees.id'], ),
        sa.ForeignKeyConstraint(['registration_id'], ['yatra_registrations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_member_devotee', 'yatra_members', ['devotee_id'])
    op.create_index('idx_member_registration', 'yatra_members', ['registration_id'])

    # Step 7: Create default pricing template from existing yatra data
    conn = op.get_bind()

    # Get unique pricing from existing yatras
    result = conn.execute(text("SELECT DISTINCT price_per_person FROM yatras WHERE deleted_at IS NULL LIMIT 1"))
    row = result.fetchone()

    if row:
        base_price = row[0]

        # Create default pricing template
        conn.execute(text("""
            INSERT INTO pricing_templates (name, description, is_active, created_at)
            VALUES ('Default Pricing Template', 'Migrated from existing yatra pricing', 1, NOW())
        """))

        # Get the template ID
        result = conn.execute(text("SELECT LAST_INSERT_ID()"))
        template_id = result.fetchone()[0]

        # Create pricing details for all 6 room categories
        room_categories = [
            ('SHARED_AC', int(base_price * 1.5)),
            ('SHARED_NON_AC', base_price),
            ('PRIVATE_AC', int(base_price * 5)),
            ('PRIVATE_NON_AC', int(base_price * 3)),
            ('FAMILY_AC', int(base_price * 2.5)),
            ('FAMILY_NON_AC', int(base_price * 1.8))
        ]

        for category, price in room_categories:
            conn.execute(text("""
                INSERT INTO pricing_template_details (template_id, room_category, price_per_person)
                VALUES (:template_id, :category, :price)
            """), {"template_id": template_id, "category": category, "price": price})

    # Step 8: Modify yatras table
    # Add new columns
    op.add_column('yatras', sa.Column('pricing_template_id', sa.Integer(), nullable=True))
    op.add_column('yatras', sa.Column('max_capacity', sa.Integer(), nullable=True))
    op.add_column('yatras', sa.Column('featured_until', sa.Date(), nullable=True))

    # Update existing yatras to use the default template
    if row:
        # nosec B608: Safe parameterized query for migration
        conn.execute(
            text("UPDATE yatras SET pricing_template_id = :template_id WHERE deleted_at IS NULL"),
            {"template_id": template_id}
        )

    # Make pricing_template_id NOT NULL after populating data
    op.alter_column('yatras', 'pricing_template_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Create foreign key constraint
    op.create_foreign_key('fk_yatras_pricing_template', 'yatras', 'pricing_templates', ['pricing_template_id'], ['id'])
    op.create_index('ix_yatras_pricing_template_id', 'yatras', ['pricing_template_id'])

    # Remove old columns from yatras
    op.drop_column('yatras', 'child_discount_percentage')
    op.drop_column('yatras', 'price_per_person')

    # Step 9: Modify yatra_registrations table
    # Add new columns
    op.add_column('yatra_registrations', sa.Column('group_id', sa.String(length=50), nullable=True))
    op.add_column('yatra_registrations', sa.Column('is_group_lead', sa.Boolean(), nullable=True, server_default='1'))

    # Generate group_id for existing registrations
    result = conn.execute(text("SELECT id FROM yatra_registrations WHERE deleted_at IS NULL"))
    for row in result:
        reg_id = row[0]
        group_id = str(uuid.uuid4())
        conn.execute(text("UPDATE yatra_registrations SET group_id = :group_id WHERE id = :id"),
                    {"group_id": group_id, "id": reg_id})

    # Make group_id NOT NULL after populating
    op.alter_column('yatra_registrations', 'group_id', nullable=False)

    # Create index on group_id
    op.create_index('idx_reg_group', 'yatra_registrations', ['group_id'])

    # Migrate accompanying_members JSON to yatra_members table
    result = conn.execute(text("""
        SELECT id, devotee_id, arrival_datetime, departure_datetime,
               accompanying_members, total_amount, dietary_requirements, medical_conditions
        FROM yatra_registrations
        WHERE deleted_at IS NULL AND accompanying_members IS NOT NULL
    """))

    for row in result:
        reg_id, devotee_id, arrival, departure, members_json, total_amount, dietary, medical = row

        # Create primary member record
        conn.execute(text("""
            INSERT INTO yatra_members (
                registration_id, devotee_id, legal_name, gender, date_of_birth,
                arrival_datetime, departure_datetime, room_category, price_charged,
                is_free, is_primary_registrant, is_registered_user,
                dietary_requirements, medical_conditions, created_at
            )
            SELECT
                :reg_id, :devotee_id, legal_name, gender, date_of_birth,
                :arrival, :departure, 'SHARED_NON_AC', :price, 0, 1, 1,
                :dietary, :medical, NOW()
            FROM devotees WHERE id = :devotee_id
        """), {
            "reg_id": reg_id, "devotee_id": devotee_id, "arrival": arrival,
            "departure": departure, "price": total_amount, "dietary": dietary, "medical": medical
        })

        # Parse and create accompanying member records
        if members_json:
            try:
                members = json.loads(members_json) if isinstance(members_json, str) else members_json
                if isinstance(members, list):
                    for member in members:
                        conn.execute(text("""
                            INSERT INTO yatra_members (
                                registration_id, devotee_id, legal_name, gender, date_of_birth,
                                arrival_datetime, departure_datetime, room_category, price_charged,
                                is_free, is_primary_registrant, is_registered_user, created_at
                            ) VALUES (
                                :reg_id, NULL, :name, :gender, :dob,
                                :arrival, :departure, 'SHARED_NON_AC', 0, 0, 0, 0, NOW()
                            )
                        """), {
                            "reg_id": reg_id,
                            "name": member.get('name', 'Unknown'),
                            "gender": member.get('gender', 'M'),
                            "dob": member.get('date_of_birth'),
                            "arrival": arrival,
                            "departure": departure
                        })
            except:
                pass  # Skip if JSON parsing fails

    # Remove old columns from yatra_registrations
    op.drop_column('yatra_registrations', 'status_history')
    op.drop_column('yatra_registrations', 'medical_conditions')
    op.drop_column('yatra_registrations', 'dietary_requirements')
    op.drop_column('yatra_registrations', 'emergency_contact_number')
    op.drop_column('yatra_registrations', 'emergency_contact_name')
    op.drop_column('yatra_registrations', 'user_remarks')
    op.drop_column('yatra_registrations', 'accompanying_members')
    op.drop_column('yatra_registrations', 'number_of_members')
    op.drop_column('yatra_registrations', 'special_room_requests')
    op.drop_column('yatra_registrations', 'floor_preference')
    op.drop_column('yatra_registrations', 'ac_preference')
    op.drop_column('yatra_registrations', 'room_preference')
    op.drop_column('yatra_registrations', 'departure_mode')
    op.drop_column('yatra_registrations', 'arrival_mode')
    op.drop_column('yatra_registrations', 'departure_datetime')
    op.drop_column('yatra_registrations', 'arrival_datetime')


def downgrade() -> None:
    """
    Downgrade from new yatra system back to old structure.

    WARNING: This will result in data loss for:
    - Individual member tracking
    - Reusable pricing templates
    - Multiple payment options per yatra
    """

    # Add back old columns to yatra_registrations
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

    # Remove new columns
    op.drop_index('idx_reg_group', 'yatra_registrations')
    op.drop_column('yatra_registrations', 'is_group_lead')
    op.drop_column('yatra_registrations', 'group_id')

    # Add back old columns to yatras
    op.add_column('yatras', sa.Column('price_per_person', sa.Integer(), nullable=True))
    op.add_column('yatras', sa.Column('child_discount_percentage', sa.Integer(), nullable=True))

    # Remove new columns from yatras
    op.drop_constraint('fk_yatras_pricing_template', 'yatras', type_='foreignkey')
    op.drop_index('ix_yatras_pricing_template_id', 'yatras')
    op.drop_column('yatras', 'featured_until')
    op.drop_column('yatras', 'max_capacity')
    op.drop_column('yatras', 'pricing_template_id')

    # Drop new tables
    op.drop_table('yatra_members')
    op.drop_table('yatra_payment_options')
    op.drop_table('payment_options')
    op.drop_table('pricing_template_details')
    op.drop_table('pricing_templates')
