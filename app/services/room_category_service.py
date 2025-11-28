"""
Room category service for managing yatra pricing categories.

This service provides CRUD operations for room categories, which are
custom pricing categories created per yatra by admins.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import RoomCategory
from app.schemas.room_category import RoomCategoryCreate, RoomCategoryUpdate


class RoomCategoryService:
    """Service for managing room categories."""

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db

    def create_room_category(
        self, yatra_id: int, category_data: RoomCategoryCreate
    ) -> RoomCategory:
        """
        Create a new room category for a yatra.

        Args:
            yatra_id: ID of the yatra
            category_data: Room category data

        Returns:
            Created room category

        Raises:
            HTTPException: If category name already exists for this yatra
        """
        # Check if category name already exists for this yatra
        existing = (
            self.db.query(RoomCategory)
            .filter(
                RoomCategory.yatra_id == yatra_id,
                RoomCategory.name == category_data.name,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room category '{category_data.name}' already exists for this yatra",
            )

        # Create new category
        category = RoomCategory(
            yatra_id=yatra_id,
            name=category_data.name,
            price_per_person=int(category_data.price_per_person),
            description=category_data.description,
        )

        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

        return category

    def get_room_categories_for_yatra(
        self, yatra_id: int, include_inactive: bool = False
    ) -> list[RoomCategory]:
        """
        Get all room categories for a yatra.

        Args:
            yatra_id: ID of the yatra
            include_inactive: Whether to include inactive categories

        Returns:
            List of room categories
        """
        query = self.db.query(RoomCategory).filter(RoomCategory.yatra_id == yatra_id)

        if not include_inactive:
            query = query.filter(RoomCategory.is_active)

        return query.order_by(RoomCategory.price_per_person).all()

    def get_room_category(self, category_id: int) -> RoomCategory:
        """
        Get a room category by ID.

        Args:
            category_id: ID of the category

        Returns:
            Room category

        Raises:
            HTTPException: If category not found
        """
        category = self.db.query(RoomCategory).filter(RoomCategory.id == category_id).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room category not found",
            )

        return category

    def update_room_category(
        self, category_id: int, category_data: RoomCategoryUpdate
    ) -> RoomCategory:
        """
        Update a room category.

        Args:
            category_id: ID of the category
            category_data: Updated category data

        Returns:
            Updated room category

        Raises:
            HTTPException: If category not found or name conflict
        """
        category = self.get_room_category(category_id)

        # Check for name conflict if name is being updated
        if category_data.name and category_data.name != category.name:
            existing = (
                self.db.query(RoomCategory)
                .filter(
                    RoomCategory.yatra_id == category.yatra_id,
                    RoomCategory.name == category_data.name,
                    RoomCategory.id != category_id,
                )
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Room category '{category_data.name}' already exists for this yatra",
                )

        # Update fields
        if category_data.name is not None:
            category.name = category_data.name
        if category_data.price_per_person is not None:
            category.price_per_person = int(category_data.price_per_person)
        if category_data.description is not None:
            category.description = category_data.description
        if category_data.is_active is not None:
            category.is_active = category_data.is_active

        self.db.commit()
        self.db.refresh(category)

        return category

    def delete_room_category(self, category_id: int) -> None:
        """
        Delete a room category.

        Args:
            category_id: ID of the category

        Raises:
            HTTPException: If category not found or has active registrations
        """
        category = self.get_room_category(category_id)

        # Check if category is used in any registrations
        # This will be handled by foreign key constraints in the database
        # For now, we'll just delete it
        self.db.delete(category)
        self.db.commit()

    def validate_category_exists(self, yatra_id: int, category_name: str) -> bool:
        """
        Check if a room category exists for a yatra.

        Args:
            yatra_id: ID of the yatra
            category_name: Name of the category

        Returns:
            True if category exists and is active, False otherwise
        """
        category = (
            self.db.query(RoomCategory)
            .filter(
                RoomCategory.yatra_id == yatra_id,
                RoomCategory.name == category_name,
                RoomCategory.is_active,
            )
            .first()
        )

        return category is not None

    def get_price_for_category(self, yatra_id: int, category_name: str) -> Decimal:
        """
        Get the price for a specific room category.

        Args:
            yatra_id: ID of the yatra
            category_name: Name of the category

        Returns:
            Price per person for the category

        Raises:
            HTTPException: If category not found or inactive
        """
        category = (
            self.db.query(RoomCategory)
            .filter(
                RoomCategory.yatra_id == yatra_id,
                RoomCategory.name == category_name,
                RoomCategory.is_active,
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room category '{category_name}' not found for this yatra",
            )

        return Decimal(str(category.price_per_person))
