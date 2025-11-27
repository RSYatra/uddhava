"""
Service for pricing template management.

This module handles CRUD operations for pricing templates and their details.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import PricingTemplate, PricingTemplateDetail
from app.schemas.pricing_template import (
    PricingTemplateCreate,
    PricingTemplateUpdate,
)

logger = logging.getLogger(__name__)


class PricingTemplateService:
    """Service for managing pricing templates."""

    def __init__(self, db: Session):
        self.db = db

    def create_template(self, template_data: PricingTemplateCreate) -> PricingTemplate:
        """
        Create a new pricing template with details.

        Args:
            template_data: Pricing template creation data

        Returns:
            Created pricing template

        Raises:
            HTTPException: If template name already exists
        """
        # Check if template name already exists
        existing = (
            self.db.query(PricingTemplate)
            .filter(PricingTemplate.name == template_data.name)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pricing template with name '{template_data.name}' already exists",
            )

        # Create template
        template = PricingTemplate(
            name=template_data.name,
            description=template_data.description,
            is_active=True,
        )
        self.db.add(template)
        self.db.flush()

        # Create pricing details
        for detail_data in template_data.pricing_details:
            detail = PricingTemplateDetail(
                template_id=template.id,
                room_category=detail_data.room_category,
                price_per_person=detail_data.price_per_person,
            )
            self.db.add(detail)

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Created pricing template: {template.name} (ID: {template.id})")
        return template

    def get_template(self, template_id: int) -> PricingTemplate:
        """
        Get a pricing template by ID.

        Args:
            template_id: Template ID

        Returns:
            Pricing template

        Raises:
            HTTPException: If template not found
        """
        template = self.db.query(PricingTemplate).filter(PricingTemplate.id == template_id).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pricing template with ID {template_id} not found",
            )
        return template

    def list_templates(self, active_only: bool = True) -> list[PricingTemplate]:
        """
        List all pricing templates.

        Args:
            active_only: If True, return only active templates

        Returns:
            List of pricing templates
        """
        query = self.db.query(PricingTemplate)
        if active_only:
            query = query.filter(PricingTemplate.is_active == True)  # noqa: E712
        return query.all()

    def update_template(
        self, template_id: int, template_data: PricingTemplateUpdate
    ) -> PricingTemplate:
        """
        Update a pricing template.

        Args:
            template_id: Template ID
            template_data: Updated template data

        Returns:
            Updated pricing template

        Raises:
            HTTPException: If template not found or name conflict
        """
        template = self.get_template(template_id)

        # Check name uniqueness if name is being updated
        if template_data.name and template_data.name != template.name:
            existing = (
                self.db.query(PricingTemplate)
                .filter(
                    PricingTemplate.name == template_data.name,
                    PricingTemplate.id != template_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Pricing template with name '{template_data.name}' already exists",
                )

        # Update template fields
        if template_data.name:
            template.name = template_data.name
        if template_data.description is not None:
            template.description = template_data.description
        if template_data.is_active is not None:
            template.is_active = template_data.is_active

        # Update pricing details if provided
        if template_data.pricing_details:
            # Delete existing details
            self.db.query(PricingTemplateDetail).filter(
                PricingTemplateDetail.template_id == template_id
            ).delete()

            # Create new details
            for detail_data in template_data.pricing_details:
                detail = PricingTemplateDetail(
                    template_id=template.id,
                    room_category=detail_data.room_category,
                    price_per_person=detail_data.price_per_person,
                )
                self.db.add(detail)

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Updated pricing template: {template.name} (ID: {template.id})")
        return template

    def delete_template(self, template_id: int) -> None:
        """
        Delete a pricing template.

        Args:
            template_id: Template ID

        Raises:
            HTTPException: If template not found or in use by yatras
        """
        template = self.get_template(template_id)

        # Check if template is in use
        from app.db.models import Yatra

        yatra_count = (
            self.db.query(Yatra)
            .filter(Yatra.pricing_template_id == template_id, Yatra.deleted_at.is_(None))
            .count()
        )
        if yatra_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete pricing template. It is used by {yatra_count} yatra(s)",
            )

        # Delete template (cascade will delete details)
        self.db.delete(template)
        self.db.commit()
        logger.info(f"Deleted pricing template: {template.name} (ID: {template.id})")

    def get_template_details(self, template_id: int) -> list[PricingTemplateDetail]:
        """
        Get pricing details for a template.

        Args:
            template_id: Template ID

        Returns:
            List of pricing details
        """
        return (
            self.db.query(PricingTemplateDetail)
            .filter(PricingTemplateDetail.template_id == template_id)
            .all()
        )
