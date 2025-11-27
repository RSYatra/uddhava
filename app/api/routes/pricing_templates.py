"""
API routes for pricing template management.

This module provides CRUD endpoints for pricing templates (admin only).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.pricing_template import (
    PricingTemplateCreate,
    PricingTemplateOut,
    PricingTemplateUpdate,
)
from app.services.pricing_template_service import PricingTemplateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing-templates", tags=["Pricing Templates"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pricing_template(
    template_data: PricingTemplateCreate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new pricing template (admin only)."""
    try:
        service = PricingTemplateService(db)
        template = service.create_template(template_data)

        # Load pricing details
        template.pricing_details = service.get_template_details(template.id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "status_code": 201,
                "message": "Pricing template created successfully",
                "data": PricingTemplateOut.model_validate(template).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pricing template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pricing template",
        )


@router.get("")
def list_pricing_templates(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all pricing templates."""
    try:
        service = PricingTemplateService(db)
        templates = service.list_templates(active_only=active_only)

        # Build response with pricing details
        templates_out = []
        for template in templates:
            pricing_details = service.get_template_details(template.id)

            # Build template dict manually
            template_dict = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "is_active": template.is_active,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None,
                "pricing_details": [
                    {
                        "id": d.id,
                        "template_id": d.template_id,
                        "room_category": d.room_category.value,
                        "price_per_person": d.price_per_person,
                    }
                    for d in pricing_details
                ],
            }
            templates_out.append(template_dict)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Pricing templates retrieved successfully",
                "data": templates_out,
            },
        )
    except Exception as e:
        logger.error(f"Error listing pricing templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list pricing templates",
        )


@router.get("/{template_id}")
def get_pricing_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific pricing template by ID."""
    try:
        service = PricingTemplateService(db)
        template = service.get_template(template_id)

        # Load pricing details
        template.pricing_details = service.get_template_details(template.id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Pricing template retrieved successfully",
                "data": PricingTemplateOut.model_validate(template).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pricing template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pricing template",
        )


@router.put("/{template_id}")
def update_pricing_template(
    template_id: int,
    template_data: PricingTemplateUpdate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a pricing template (admin only)."""
    try:
        service = PricingTemplateService(db)
        template = service.update_template(template_id, template_data)

        # Load pricing details
        template.pricing_details = service.get_template_details(template.id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Pricing template updated successfully",
                "data": PricingTemplateOut.model_validate(template).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pricing template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pricing template",
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing_template(
    template_id: int,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a pricing template (admin only)."""
    try:
        service = PricingTemplateService(db)
        service.delete_template(template_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pricing template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete pricing template",
        )
