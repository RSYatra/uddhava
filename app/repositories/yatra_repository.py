"""
Data access layer for Yatra model.

This repository handles all database operations for yatras with clean separation
of concerns from business logic.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Yatra, YatraRegistration, YatraStatus


class YatraRepository:
    """Repository for Yatra data access operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, yatra_data: dict) -> Yatra:
        """Create new yatra."""
        yatra = Yatra(**yatra_data)
        self.db.add(yatra)
        self.db.flush()
        return yatra

    def get_by_id(self, yatra_id: int, include_deleted: bool = False) -> Yatra | None:
        """Get yatra by ID."""
        query = self.db.query(Yatra).filter(Yatra.id == yatra_id)
        if not include_deleted:
            query = query.filter(Yatra.deleted_at.is_(None))
        return query.first()

    def get_by_slug(self, slug: str) -> Yatra | None:
        """Get yatra by URL slug."""
        return self.db.query(Yatra).filter(Yatra.slug == slug, Yatra.deleted_at.is_(None)).first()

    def list_all(
        self,
        status: YatraStatus | None = None,
        upcoming_only: bool = False,
        featured_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Yatra]:
        """List yatras with filters."""
        query = self.db.query(Yatra).filter(Yatra.deleted_at.is_(None))

        if status:
            query = query.filter(Yatra.status == status)

        if upcoming_only:
            query = query.filter(Yatra.start_date >= date.today())

        if featured_only:
            query = query.filter(Yatra.is_featured == True)  # noqa: E712

        return query.order_by(Yatra.start_date).offset(skip).limit(limit).all()

    def update(self, yatra: Yatra, update_data: dict) -> Yatra:
        """Update yatra fields."""
        for key, value in update_data.items():
            if value is not None and hasattr(yatra, key):
                setattr(yatra, key, value)
        self.db.flush()
        return yatra

    def soft_delete(self, yatra: Yatra) -> None:
        """Soft delete yatra."""
        from datetime import UTC, datetime

        yatra.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        self.db.flush()

    def get_registration_count(self, yatra_id: int, status: str | None = None) -> int:
        """Get count of registrations for a yatra."""
        query = self.db.query(func.count(YatraRegistration.id)).filter(
            YatraRegistration.yatra_id == yatra_id,
            YatraRegistration.deleted_at.is_(None),
        )
        if status:
            query = query.filter(YatraRegistration.status == status)
        return query.scalar() or 0
