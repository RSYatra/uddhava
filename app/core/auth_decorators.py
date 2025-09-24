"""
Authentication and authorization decorators for clean endpoint protection.

This module provides reusable decorators that eliminate code duplication
in route handlers while providing flexible security controls.
"""

import functools
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.models import Devotee, UserRole


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint.

    Usage:
        @require_auth
        def my_endpoint():
            pass
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user from kwargs if it exists
        current_user = kwargs.get("current_user")
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await func(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles: UserRole):
    """
    Decorator to require specific role(s) for an endpoint.

    Usage:
        @require_role(UserRole.ADMIN)
        def admin_only_endpoint():
            pass

        @require_role(UserRole.ADMIN, UserRole.USER)
        def multi_role_endpoint():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user: Devotee = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if current_user.role not in allowed_roles:
                role_names = [role.value for role in allowed_roles]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {role_names}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_owner_or_admin(user_id_param: str = "user_id"):
    """
    Decorator to require user ownership or admin role for an endpoint.

    Args:
        user_id_param: Name of the parameter containing the user ID to check

    Usage:
        @require_owner_or_admin('user_id')
        def update_user(user_id: int, current_user: Devotee = Depends(get_current_user)):
            pass

        @require_owner_or_admin('target_user_id')
        def custom_endpoint(
            target_user_id: int,
            current_user: Devotee = Depends(get_current_user)
        ):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user: Devotee = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get the user_id from function parameters
            target_user_id = kwargs.get(user_id_param)
            if target_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required parameter: {user_id_param}",
                )

            # Check if user is admin or owns the resource
            if (
                current_user.role != UserRole.ADMIN
                and current_user.id != target_user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Access denied: You can only access your own resources "
                        "or need admin privileges"
                    ),
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for an endpoint.

    Usage:
        @require_admin
        def admin_endpoint(current_user: Devotee = Depends(get_current_user)):
            pass
    """
    return require_role(UserRole.ADMIN)(func)


def inject_current_user(func: Callable) -> Callable:
    """
    Decorator to automatically inject current_user dependency.

    This eliminates the need to manually add the Depends(get_current_user)
    parameter to every protected endpoint.

    Usage:
        @inject_current_user
        @require_auth
        def my_endpoint(user_id: int, current_user: Devotee):
            # current_user is automatically injected
            pass
    """
    # Get the original function signature
    import inspect

    sig = inspect.signature(func)

    # Check if current_user is already in the signature
    if "current_user" not in sig.parameters:
        # Add current_user parameter with dependency injection
        @functools.wraps(func)
        async def wrapper(
            *args, current_user: Devotee = Depends(get_current_user), **kwargs
        ):
            # Inject current_user into kwargs
            kwargs["current_user"] = current_user
            return await func(*args, **kwargs)

    else:
        # current_user already exists, just pass through
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

    return wrapper


# Convenience decorators combining common patterns
def protected_endpoint(func: Callable) -> Callable:
    """
    Convenience decorator for standard protected endpoints.

    Combines: inject_current_user + require_auth

    Usage:
        @protected_endpoint
        def my_endpoint(user_id: int):
            # current_user is available in function context
            pass
    """
    return inject_current_user(require_auth(func))


def admin_only_endpoint(func: Callable) -> Callable:
    """
    Convenience decorator for admin-only endpoints.

    Combines: inject_current_user + require_admin

    Usage:
        @admin_only_endpoint
        def admin_function():
            pass
    """
    return inject_current_user(require_admin(func))


def owner_or_admin_endpoint(user_id_param: str = "user_id"):
    """
    Convenience decorator for owner-or-admin endpoints.

    Combines: inject_current_user + require_owner_or_admin

    Usage:
        @owner_or_admin_endpoint('user_id')
        def update_profile(user_id: int):
            pass
    """

    def decorator(func: Callable) -> Callable:
        return inject_current_user(require_owner_or_admin(user_id_param)(func))

    return decorator
