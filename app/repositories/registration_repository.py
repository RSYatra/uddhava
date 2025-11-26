"""
Data access layer for YatraRegistration model.

This repository handles all database operations for registrations with audit trail.
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import RegistrationStatus, YatraRegistration


class RegistrationRepository:
    """Repository for YatraRegistration data access operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, reg_data: dict) -> YatraRegistration:
        """Create new registration with auto-generated registration number."""
        reg_number = self._generate_registration_number()
        reg_data["registration_number"] = reg_number

        registration = YatraRegistration(**reg_data)
        self.db.add(registration)
        self.db.flush()
        return registration

    def get_by_id(self, reg_id: int, include_deleted: bool = False) -> YatraRegistration | None:
        """Get registration by ID."""
        query = self.db.query(YatraRegistration).filter(YatraRegistration.id == reg_id)
        if not include_deleted:
            query = query.filter(YatraRegistration.deleted_at.is_(None))
        return query.first()

    def get_by_registration_number(self, reg_number: str) -> YatraRegistration | None:
        """Get registration by registration number."""
        return (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.registration_number == reg_number,
                YatraRegistration.deleted_at.is_(None),
            )
            .first()
        )

    def check_duplicate_registration(self, yatra_id: int, devotee_id: int) -> bool:
        """Check if devotee already has active registration for yatra."""
        active_statuses = [
            RegistrationStatus.PENDING,
            RegistrationStatus.PAYMENT_SUBMITTED,
            RegistrationStatus.PAYMENT_VERIFIED,
            RegistrationStatus.CONFIRMED,
        ]

        exists = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.yatra_id == yatra_id,
                YatraRegistration.devotee_id == devotee_id,
                YatraRegistration.status.in_(active_statuses),
                YatraRegistration.deleted_at.is_(None),
            )
            .first()
        )

        return exists is not None

    def list_by_devotee(
        self,
        devotee_id: int,
        status: RegistrationStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[YatraRegistration]:
        """List registrations for a devotee."""
        query = self.db.query(YatraRegistration).filter(
            YatraRegistration.devotee_id == devotee_id,
            YatraRegistration.deleted_at.is_(None),
        )

        if status:
            query = query.filter(YatraRegistration.status == status)

        return query.order_by(YatraRegistration.created_at.desc()).offset(skip).limit(limit).all()

    def list_by_yatra(
        self,
        yatra_id: int,
        status: RegistrationStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[YatraRegistration]:
        """List registrations for a yatra."""
        query = self.db.query(YatraRegistration).filter(
            YatraRegistration.yatra_id == yatra_id,
            YatraRegistration.deleted_at.is_(None),
        )

        if status:
            query = query.filter(YatraRegistration.status == status)

        return query.order_by(YatraRegistration.created_at).offset(skip).limit(limit).all()

    def update_status(
        self,
        registration: YatraRegistration,
        new_status: RegistrationStatus,
        admin_id: int | None,
        remarks: str | None,
    ) -> YatraRegistration:
        """Update registration status with audit trail."""
        old_status = registration.status
        registration.status = new_status  # type: ignore[assignment]

        # Add to status history
        history_entry = {
            "from_status": old_status.value,
            "to_status": new_status.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "changed_by": admin_id,
            "remarks": remarks,
        }

        if registration.status_history:
            registration.status_history.append(history_entry)  # type: ignore[attr-defined]
        else:
            registration.status_history = [history_entry]  # type: ignore[assignment]

        if admin_id:
            registration.reviewed_by = admin_id  # type: ignore[assignment]
            registration.reviewed_at = datetime.now(UTC)  # type: ignore[assignment]

        self.db.flush()
        return registration

    def _generate_registration_number(self) -> str:
        """Generate unique registration number: YTR-YYYY-NNNN."""
        year = datetime.now().year

        # Get count of registrations this year
        count = (
            self.db.query(func.count(YatraRegistration.id))
            .filter(YatraRegistration.registration_number.like(f"YTR-{year}-%"))
            .scalar()
            or 0
        )

        return f"YTR-{year}-{count + 1:04d}"
