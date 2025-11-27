"""
FastAPI dependency functions for authentication and authorization.

These dependencies provide reusable access control without using *args, **kwargs,
ensuring FastAPI can properly introspect function signatures for OpenAPI generation.
"""

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.models import Devotee, UserRole


def require_admin(
    current_user: Devotee = Depends(get_current_user),
) -> Devotee:
    """
    Dependency that ensures the current user has admin role.

    Args:
        current_user: Currently authenticated user (injected by FastAPI)

    Returns:
        Devotee: The current user if they are an admin

    Raises:
        HTTPException: 403 if user is not an admin

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            admin: Devotee = Depends(require_admin),
            db: Session = Depends(get_db),
        ):
            # admin is guaranteed to be an admin user
            ...
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def check_resource_access(
    current_user: Devotee,
    resource_owner_id: int,
    resource_name: str = "resource",
) -> None:
    """
    Helper function to check if user can access a resource.

    Call this in your endpoint after fetching the resource.

    Args:
        current_user: Currently authenticated user
        resource_owner_id: ID of the resource owner
        resource_name: Name of the resource (for error message)

    Raises:
        HTTPException: 403 if user doesn't have access

    Usage:
        @router.get("/devotees/{devotee_id}")
        async def get_devotee(
            devotee_id: int,
            current_user: Devotee = Depends(get_current_user),
            db: Session = Depends(get_db),
        ):
            check_resource_access(current_user, devotee_id, "devotee profile")
            devotee = service.get_devotee(devotee_id)
            ...
    """
    if current_user.role != UserRole.ADMIN and current_user.id != resource_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You can only access your own {resource_name} or need admin privileges",
        )
