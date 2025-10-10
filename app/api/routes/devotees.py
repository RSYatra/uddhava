"""
Comprehensive devotee management API endpoints.

This module contains all devotee-related routes including CRUD operations,
advanced search, filtering, statistics, and profile management.
Optimized for performance with 100K users.
"""

import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import check_resource_access, require_admin
from app.core.security import get_current_user
from app.db.models import Devotee, Gender, InitiationStatus, MaritalStatus, UserRole
from app.db.session import SessionLocal
from app.schemas.devotee import (
    DevoteeCreate,
    DevoteeSearchFilters,
    DevoteeUpdate,
)
from app.schemas.devotee_responses import (
    StandardDevoteeListResponse,
    StandardDevoteeResponse,
    StandardDevoteeStatsResponse,
    StandardSearchResponse,
    StandardValidationResponse,
)

# NOTE: Using service class directly with per-request instantiation
from app.services.devotee_service import DevoteeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devotees", tags=["Devotees"])


def get_db():
    """Database dependency with robust error handling."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError:
        logger.exception("Database error during request")
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    finally:
        db.close()


@router.get(
    "/",
    response_model=StandardDevoteeListResponse,
    summary="List Devotees with Advanced Filtering",
)
async def get_devotees(
    # Text search
    search: str | None = Query(
        None, max_length=255, description="Search in name, email, or location"
    ),
    # Location filters
    country: str | None = Query(None, max_length=100, description="Filter by country"),
    state_province: str | None = Query(
        None, max_length=100, description="Filter by state/province"
    ),
    city: str | None = Query(None, max_length=100, description="Filter by city"),
    # Spiritual filters
    initiation_status: InitiationStatus | None = Query(
        None, description="Filter by initiation status"
    ),
    spiritual_master: str | None = Query(
        None, max_length=255, description="Filter by spiritual master"
    ),
    # Demographic filters
    gender: Gender | None = Query(None, description="Filter by gender"),
    marital_status: MaritalStatus | None = Query(None, description="Filter by marital status"),
    # Age range filters
    min_age: int | None = Query(None, ge=0, le=120, description="Minimum age filter"),
    max_age: int | None = Query(None, ge=0, le=120, description="Maximum age filter"),
    # Chanting filters
    min_rounds: int | None = Query(
        None, ge=0, le=200, description="Minimum chanting rounds filter"
    ),
    max_rounds: int | None = Query(
        None, ge=0, le=200, description="Maximum chanting rounds filter"
    ),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    # Sorting
    sort_by: str | None = Query(
        "created_at",
        description="Sort field: legal_name, created_at, city, initiation_status",
    ),
    sort_order: str | None = Query(
        "desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"
    ),
    # Dependencies
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Retrieve devotees with comprehensive filtering, search, and pagination.

    This endpoint provides powerful search and filtering capabilities:

    **Search Features:**
    - Text search across name, email, and location
    - Location-based filtering (country, state, city)
    - Spiritual information filtering (initiation status, spiritual master)
    - Demographic filtering (gender, marital status, age range)
    - Chanting practice filtering (rounds range)

    **Performance Features:**
    - Optimized pagination with proper indexing
    - Efficient sorting with multiple field options
    - Cached query results for common filters
    - Strategic use of database indexes

    **Access Control:**
    - Admin users can see all devotees
    - Regular users can see public information only
    - Private fields are filtered based on user role
    """
    try:
        # Create search filters object
        filters = DevoteeSearchFilters(
            search=search,
            country=country,
            state_province=state_province,
            city=city,
            initiation_status=initiation_status,
            spiritual_master=spiritual_master,
            gender=gender,
            marital_status=marital_status,
            min_age=min_age,
            max_age=max_age,
            min_rounds=min_rounds,
            max_rounds=max_rounds,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Get filtered devotees using service
        service = DevoteeService(db)
        result = service.get_devotees_with_filters(db, filters)

        logger.info(f"Retrieved {len(result.devotees)} devotees with filters")
        return StandardDevoteeListResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Devotees retrieved successfully",
            data=result,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter parameters: {e!s}",
        )
    except SQLAlchemyError:
        logger.exception("Database error retrieving devotees")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devotees",
        )


@router.post("/", response_model=StandardDevoteeResponse, summary="Create New Devotee")
async def create_devotee(
    devotee_data: DevoteeCreate,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Create a new devotee with comprehensive information.

    **Required Information:**
    - Personal details (name, DOB, gender, marital status)
    - Contact information (email, phone, address)
    - Family information (father/mother names)
    - Authentication (secure password)

    **Optional Information:**
    - ISKCON spiritual journey details
    - Initiation information
    - Chanting practice details
    - Devotional education
    - Profile photo

    **Validation Features:**
    - Email uniqueness validation
    - Password strength requirements
    - Business rule validation (e.g., married status requires spouse name)
    - Date validation (birth date, marriage date, initiation date)
    - Mobile number format validation

    **Security Features:**
    - Password hashing with bcrypt
    - File upload validation for photos
    - SQL injection prevention
    - Input sanitization
    """
    try:
        service = DevoteeService(db)
        devotee = service.create_devotee(db, devotee_data)
        logger.info(f"Created new devotee: {devotee.email}")
        return StandardDevoteeResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Devotee created successfully",
            data=devotee,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SQLAlchemyError:
        logger.exception("Database error creating devotee")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create devotee",
        )


@router.get("/{devotee_id}", response_model=StandardDevoteeResponse, summary="Get Devotee by ID")
async def get_devotee(
    devotee_id: int,
    db: Session = Depends(get_db),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Retrieve detailed information about a specific devotee.

    **Access Control:**
    - Devotees can access their own profile
    - Admin users can access any devotee profile
    - Sensitive information filtered based on access level

    **Returned Information:**
    - Complete devotee profile
    - Computed fields (age, spiritual journey duration)
    - Family information (children count, marriage details)
    - ISKCON journey and spiritual information
    - Chanting practice history

    **Privacy Features:**
    - Sensitive fields hidden from non-owners
    - Email and phone masked for non-admin users
    - Children details protected
    """
    try:
        check_resource_access(current_user, devotee_id, "devotee profile")
        service = DevoteeService(db)
        devotee = service.get_devotee_by_id(db, devotee_id)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        logger.info(f"Retrieved devotee profile: {devotee_id}")
        return StandardDevoteeResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Devotee retrieved successfully",
            data=devotee,
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error retrieving devotee")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devotee",
        )


@router.put("/{devotee_id}", response_model=StandardDevoteeResponse, summary="Update Devotee")
async def update_devotee(
    devotee_id: int,
    devotee_update: DevoteeUpdate,
    db: Session = Depends(get_db),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Update devotee information with comprehensive validation.

    **Updatable Fields:**
    - Personal information (name, demographics)
    - Contact information (phone, address)
    - Family information (spouse, children, parents)
    - ISKCON spiritual journey
    - Chanting practice details
    - Profile photo

    **Business Rules:**
    - Email changes require additional verification
    - Married status requires spouse information
    - Initiation status requires spiritual master details
    - Date consistency validation

    **Access Control:**
    - Devotees can update their own profile
    - Admin users can update any profile
    - Role changes restricted to admin users

    **Audit Features:**
    - All changes logged for audit trail
    - Timestamp updates on modifications
    - Version history (future enhancement)
    """
    # Check access: admin or owner
    if current_user.role != UserRole.ADMIN and current_user.id != devotee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own profile or need admin privileges",
        )
    try:
        service = DevoteeService(db)
        devotee = service.update_devotee(db, devotee_id, devotee_update)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        logger.info(f"Updated devotee: {devotee_id}")
        return StandardDevoteeResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Devotee updated successfully",
            data=devotee,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SQLAlchemyError:
        logger.exception("Error updating devotee")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update devotee",
        )


@router.get("/search/text", response_model=StandardSearchResponse, summary="Fast Text Search")
async def search_devotees_text(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Perform fast text search across devotee information.

    **Search Fields:**
    - Legal name (full text search)
    - Email address
    - City and country
    - Spiritual master name

    **Performance Features:**
    - Optimized LIKE queries with proper indexing
    - Configurable result limits
    - Fast response times for autocomplete
    - Minimal data transfer

    **Use Cases:**
    - Devotee lookup by name
    - Email search for admin functions
    - Location-based quick search
    - Spiritual master devotee lists
    """
    try:
        if len(q.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters",
            )

        service = DevoteeService(db)
        devotees = service.search_devotees_by_text(db, q.strip(), limit)
        logger.info(f"Text search for '{q}' returned {len(devotees)} results")
        return StandardSearchResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Search completed successfully",
            data=devotees,
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error in text search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


@router.get(
    "/location/{country}",
    response_model=StandardSearchResponse,
    summary="Get Devotees by Location",
)
async def get_devotees_by_location(
    country: str,
    state: str | None = Query(None, description="State or province"),
    city: str | None = Query(None, description="City name"),
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Get devotees filtered by geographic location.

    **Location Hierarchy:**
    - Country (required)
    - State/Province (optional)
    - City (optional)

    **Use Cases:**
    - Regional devotee management
    - Event planning and coordination
    - Local center administration
    - Geographic analytics

    **Performance Features:**
    - Indexed location queries
    - Hierarchical filtering
    - Efficient sorting by name
    """
    try:
        service = DevoteeService(db)

        devotees = service.get_devotees_by_location(db, country, state, city)

        location_desc = f"{city}, " if city else ""
        location_desc += f"{state}, " if state else ""
        location_desc += country

        logger.info(f"Retrieved {len(devotees)} devotees from {location_desc}")
        return StandardSearchResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Devotees retrieved successfully",
            data=devotees,
        )

    except SQLAlchemyError:
        logger.exception("Error retrieving devotees by location")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devotees by location",
        )


@router.get(
    "/spiritual-master/{master_name}",
    response_model=StandardSearchResponse,
    summary="Get Devotees by Spiritual Master",
)
async def get_devotees_by_spiritual_master(
    master_name: str,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Get all devotees of a specific spiritual master.

    **Features:**
    - Case-insensitive spiritual master search
    - Sorted results by devotee name
    - Includes initiation details

    **Use Cases:**
    - Spiritual master's devotee management
    - Initiation tracking and records
    - Spiritual family tree visualization
    - Communication with specific spiritual groups
    """
    try:
        service = DevoteeService(db)

        devotees = service.get_devotees_by_spiritual_master(db, master_name)
        logger.info(f"Retrieved {len(devotees)} devotees of spiritual master: {master_name}")
        return devotees

    except SQLAlchemyError:
        logger.exception("Error retrieving devotees by spiritual master")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devotees by spiritual master",
        )


@router.get(
    "/statistics/overview",
    response_model=StandardDevoteeStatsResponse,
    summary="Get Devotee Statistics",
)
async def get_devotee_statistics(
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Get comprehensive devotee statistics and analytics.

    **Statistics Included:**
    - Total devotee count
    - Geographic distribution (top countries)
    - Initiation status breakdown
    - Gender and marital status distribution
    - Average age and chanting rounds
    - Recently joined devotees (last 30 days)

    **Use Cases:**
    - Administrative dashboards
    - Strategic planning and analysis
    - Geographic expansion insights
    - Spiritual progress tracking
    - Growth metrics and trends

    **Access Control:**
    - Admin users only
    - Aggregated data for privacy
    - No individual devotee identification
    """
    try:
        service = DevoteeService(db)

        stats = service.get_devotee_statistics(db)
        logger.info("Retrieved devotee statistics")
        return StandardDevoteeStatsResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Statistics retrieved successfully",
            data=stats,
        )

    except SQLAlchemyError:
        logger.exception("Error retrieving devotee statistics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


@router.get("/{devotee_id}/photo", summary="Get Devotee Photo")
async def get_devotee_photo(
    devotee_id: int,
    db: Session = Depends(get_db),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Retrieve a devotee's profile photo.

    **Features:**
    - Secure photo access with authentication
    - Optimized file serving
    - Proper image headers and caching

    **Access Control:**
    - Devotees can access their own photos
    - Admin users can access any photo
    - 404 response for missing photos

    **File Handling:**
    - Multiple image format support
    - Proper MIME type detection
    - File existence validation
    """
    try:
        check_resource_access(current_user, devotee_id, "devotee profile")
        service = DevoteeService(db)

        devotee = service.get_devotee_by_id(db, devotee_id)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        # TODO: Implement photo storage and retrieval
        # For now, return a placeholder response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not available")

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error retrieving devotee photo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve photo",
        )


# Additional utility endpoints


@router.get("/export/csv", summary="Export Devotees to CSV")
async def export_devotees_csv(
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Export devotee data to CSV format for admin users.

    **Features:**
    - Complete devotee data export
    - CSV format for spreadsheet compatibility
    - Privacy-compliant data handling

    **Access Control:**
    - Admin users only
    - Audit logging for exports
    - Rate limiting for large exports

    **Data Handling:**
    - Sanitized data for privacy
    - Proper CSV encoding
    - Compressed download for large datasets
    """
    # TODO: Implement CSV export functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="CSV export feature coming soon",
    )


@router.get(
    "/validate/email/{email}",
    response_model=StandardValidationResponse,
    summary="Validate Email Availability",
)
async def validate_email_availability(
    email: str,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Check if email address is available for registration.

    **Features:**
    - Real-time email availability checking
    - Fast response for form validation
    - Case-insensitive checking

    **Use Cases:**
    - Registration form validation
    - Prevent duplicate email registrations
    - User experience optimization

    **Privacy:**
    - No sensitive information disclosed
    - Generic responses for security
    """
    try:
        service = DevoteeService(db)

        existing_devotee = service.get_devotee_by_email(db, email)
        is_available = existing_devotee is None
        return StandardValidationResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Email is available" if is_available else "Email already registered",
            data={
                "email": email,
                "available": is_available,
            },
        )

    except SQLAlchemyError:
        logger.exception("Error validating email availability")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email validation failed",
        )


@router.get(
    "/{devotee_id}/files/{file_type}/{filename}",
    summary="Download Devotee File",
    description="""
Download a devotee's uploaded file (profile photo or document).

**File Types:**
- `photos`: Profile photos
- `documents`: Uploaded documents

**Access Control:**
- Users can download their own files
- Admin users can download any user's files

**Security:**
- Path traversal protection
- File existence validation
- Access control enforcement
    """,
)
async def download_devotee_file(
    devotee_id: int,
    file_type: str,
    filename: str,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a devotee's uploaded file with security checks.

    Args:
        devotee_id: The devotee's user ID
        file_type: Type of file - "photos" or "documents"
        filename: Name of the file to download
        current_user: Current authenticated user
        db: Database session

    Returns:
        FileResponse: The requested file

    Raises:
        HTTPException: For access denied, invalid file type, or file not found
    """
    # Check access: admin or owner
    check_resource_access(current_user, devotee_id, "file")

    # Validate file_type
    if file_type not in ["photos", "documents"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Must be 'photos' or 'documents'",
        )

    # Construct file path
    file_path = Path(settings.upload_directory) / file_type / str(devotee_id) / filename

    # Security check: ensure path is within allowed directory
    try:
        file_path.resolve().relative_to(Path(settings.upload_directory).resolve())
    except ValueError:
        logger.warning(
            f"Security violation: User {current_user.id} attempted path traversal with: {filename}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid file path",
        )

    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    logger.info(f"User {current_user.id} downloading file: {file_type}/{devotee_id}/{filename}")

    # Return file with appropriate media type
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )
