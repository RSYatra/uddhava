"""
Standardized API response utilities.

This module provides reusable utilities for building consistent API responses
across all endpoints. All responses follow the standard format:
{
    "success": bool,
    "status_code": int,
    "message": str,
    "data": Any | None
}

This ensures:
- Consistent frontend consumption
- Type-safe response building
- DRY principle adherence
- Scalable architecture
"""

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class StandardHTTPException(HTTPException):
    """
    Custom HTTPException that carries standard response format.

    This exception is designed to be caught by the global exception handler
    and automatically converted to the standard response format.

    Usage:
        raise StandardHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Resource not found",
            success=False,
            data=None
        )
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        success: bool = False,
        data: Any = None,
    ):
        """
        Initialize standard HTTP exception.

        Args:
            status_code: HTTP status code (e.g., 404, 500)
            message: Human-readable error message
            success: Success flag (default: False for exceptions)
            data: Optional additional data
        """
        self.status_code = status_code
        self.message = message
        self.success = success
        self.data = data
        # Set detail for compatibility with FastAPI's HTTPException
        super().__init__(status_code=status_code, detail=message)


def success_response(
    status_code: int = status.HTTP_200_OK,
    message: str = "Operation successful",
    data: Any = None,
) -> JSONResponse:
    """
    Create a standardized success response.

    Args:
        status_code: HTTP status code (200, 201, etc.)
        message: Success message
        data: Response data payload

    Returns:
        JSONResponse with standard format

    Example:
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Yatra created successfully",
            data={"id": 1, "name": "Vrindavan Yatra"}
        )
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )


def error_response(
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    message: str = "An error occurred",
    data: Any = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP error status code (400, 401, 403, 404, 500, etc.)
        message: Error message
        data: Optional error details

    Returns:
        JSONResponse with standard format

    Example:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Yatra not found",
            data=None
        )
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
    )


def validation_error_response(
    message: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """
    Create a standardized validation error response.

    Args:
        message: Primary validation error message
        errors: Optional list of detailed validation errors

    Returns:
        JSONResponse with standard format (422 status)

    Example:
        return validation_error_response(
            message="Invalid input data",
            errors=[{"field": "email", "error": "Invalid email format"}]
        )
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": message,
            "data": {"errors": errors} if errors else None,
        },
    )


def created_response(
    message: str = "Resource created successfully",
    data: Any = None,
) -> JSONResponse:
    """
    Convenience method for 201 Created responses.

    Args:
        message: Success message
        data: Created resource data

    Returns:
        JSONResponse with 201 status and standard format
    """
    return success_response(
        status_code=status.HTTP_201_CREATED,
        message=message,
        data=data,
    )


def no_content_response() -> JSONResponse:
    """
    Convenience method for 204 No Content responses.

    Returns:
        JSONResponse with 204 status and no body
    """
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )


def unauthorized_response(
    message: str = "Authentication required",
) -> JSONResponse:
    """
    Convenience method for 401 Unauthorized responses.

    Args:
        message: Authentication error message

    Returns:
        JSONResponse with 401 status and standard format
    """
    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message=message,
    )


def forbidden_response(
    message: str = "Access denied",
) -> JSONResponse:
    """
    Convenience method for 403 Forbidden responses.

    Args:
        message: Authorization error message

    Returns:
        JSONResponse with 403 status and standard format
    """
    return error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message=message,
    )


def not_found_response(
    message: str = "Resource not found",
) -> JSONResponse:
    """
    Convenience method for 404 Not Found responses.

    Args:
        message: Not found error message

    Returns:
        JSONResponse with 404 status and standard format
    """
    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message=message,
    )


def bad_request_response(
    message: str = "Bad request",
    data: Any = None,
) -> JSONResponse:
    """
    Convenience method for 400 Bad Request responses.

    Args:
        message: Bad request error message
        data: Optional error details

    Returns:
        JSONResponse with 400 status and standard format
    """
    return error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        data=data,
    )


def server_error_response(
    message: str = "Internal server error",
) -> JSONResponse:
    """
    Convenience method for 500 Internal Server Error responses.

    Args:
        message: Server error message

    Returns:
        JSONResponse with 500 status and standard format
    """
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
    )
