"""
Google Cloud Storage service for file uploads.

Provides simple, clean interface for uploading, downloading, and managing
user files in GCS with descriptive filenames.
"""

import json
import logging
import mimetypes
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from google.oauth2 import service_account

from app.core.config import settings
from app.core.responses import StandardHTTPException

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for managing file uploads to Google Cloud Storage.

    Handles file validation, sanitization, upload, download, and deletion
    with descriptive filenames organized by user ID.
    """

    def __init__(self):
        """Initialize GCS client and bucket."""
        try:
            # Try to load credentials from environment variable (for Render/production)
            gcs_creds_json = os.getenv("GCS_CREDENTIALS_JSON")
            if gcs_creds_json:
                # Load from environment variable (Render, production)
                creds_dict = json.loads(gcs_creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = storage.Client(
                    project=settings.gcs_project_id, credentials=credentials
                )
                logger.info(
                    "Initialized StorageService with service account credentials from environment"
                )
            else:
                # Use Application Default Credentials (local development, GCP Cloud Run)
                self.client = storage.Client(project=settings.gcs_project_id)
                logger.info("Initialized StorageService with Application Default Credentials")

            self.bucket = self.client.bucket(settings.gcs_bucket_name)
            logger.info(f"Initialized StorageService for bucket: {settings.gcs_bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize StorageService: {e}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be GCS-safe and descriptive.

        Converts to lowercase, replaces spaces with underscores,
        removes special characters except underscores, hyphens, and dots.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Convert to lowercase
        filename = filename.lower()

        # Replace spaces with underscores
        filename = filename.replace(" ", "_")

        # Remove special characters except underscores, hyphens, dots
        filename = re.sub(r"[^a-z0-9._-]", "", filename)

        # Remove multiple consecutive underscores
        filename = re.sub(r"_+", "_", filename)

        # Remove leading/trailing underscores and dots
        filename = filename.strip("_.")

        return filename

    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate file size and extension.

        Args:
            file: FastAPI UploadFile object

        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        max_size = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise StandardHTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                message=f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size ({settings.max_file_size_mb}MB)",
                success=False,
                data=None,
            )

        # Check file extension
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            allowed_extensions = (
                settings.allowed_image_extensions + settings.allowed_document_extensions
            )

            if file_ext not in allowed_extensions:
                raise StandardHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}",
                    success=False,
                    data=None,
                )

    def _get_content_type(self, filename: str) -> str:
        """
        Detect content type from filename extension.

        Args:
            filename: Filename with extension

        Returns:
            MIME content type
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    def upload_file(self, file: UploadFile, user_id: int, file_purpose: str) -> dict:
        """
        Upload file to GCS with descriptive name.

        Args:
            file: FastAPI UploadFile object
            user_id: User ID for path organization
            file_purpose: Descriptive name (e.g., 'profile_photo', 'bhakti_shastri_certificate')

        Returns:
            dict: File metadata with keys:
                - name: Original filename
                - gcs_path: Full GCS path
                - size: File size in bytes
                - content_type: MIME type
                - uploaded_at: ISO timestamp
                - purpose: Sanitized file purpose

        Raises:
            HTTPException: If upload fails
        """
        try:
            # Validate file
            self._validate_file(file)

            # Get file extension
            file_ext = Path(file.filename).suffix.lower() if file.filename else ""

            # Sanitize purpose and create filename
            sanitized_purpose = self._sanitize_filename(file_purpose)
            if not sanitized_purpose:
                sanitized_purpose = "file"

            # Payment screenshots: Use directory structure with UUID for multiple uploads
            # Format: {group_id}/{uuid}.{ext} (e.g., grp-2026-5-002/8e6cca15.jpg)
            # Regular files: Use purpose as filename (e.g., profile_photo.jpg)
            if sanitized_purpose.startswith("grp-"):
                filename = f"{sanitized_purpose}/{uuid4().hex[:8]}{file_ext}"
            else:
                filename = f"{sanitized_purpose}{file_ext}"

            # Create GCS path: {user_id}/{filename}
            gcs_path = f"{user_id}/{filename}"

            # Get file size
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            # Detect content type
            content_type = self._get_content_type(filename)

            # Create blob and upload
            blob = self.bucket.blob(gcs_path)

            # Set metadata
            blob.metadata = {
                "original_filename": file.filename or filename,
                "uploaded_by": str(user_id),
                "upload_date": datetime.now(UTC).isoformat(),
                "purpose": sanitized_purpose,
            }

            # Upload file
            file_content = file.file.read()
            blob.upload_from_string(file_content, content_type=content_type)

            logger.info(
                f"Uploaded file for user {user_id}: {gcs_path} ({file_size} bytes, {content_type})"
            )

            # Return metadata
            return {
                "name": file.filename or filename,
                "gcs_path": gcs_path,
                "size": file_size,
                "content_type": content_type,
                "uploaded_at": datetime.now(UTC).isoformat(),
                "purpose": sanitized_purpose,
            }

        except HTTPException:
            raise
        except GoogleCloudError as e:
            logger.error(f"GCS error uploading file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to upload file to cloud storage. Please try again.",
                success=False,
                data=None,
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to upload file. Please try again.",
                success=False,
                data=None,
            )

    def download_file(self, user_id: int, filename: str) -> tuple[bytes, str]:
        """
        Download file from GCS.

        Args:
            user_id: User ID
            filename: Filename or path to download (e.g., "profile_photo.jpg" or "grp-2026-4-001/abc123.jpg")

        Returns:
            tuple: (file_content, content_type)

        Raises:
            HTTPException: If download fails or file not found
        """
        try:
            # For directory-based paths (containing /), don't sanitize to preserve structure
            # For simple filenames, sanitize to prevent path traversal
            if "/" in filename:
                # Directory-based path - validate it doesn't try to escape user directory
                if filename.startswith("../") or "/../" in filename:
                    raise StandardHTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Invalid file path",
                        success=False,
                        data=None,
                    )
                sanitized_filename = filename.lower()  # Just lowercase for consistency
            else:
                # Simple filename - full sanitization
                sanitized_filename = self._sanitize_filename(filename)

            # Create GCS path
            gcs_path = f"{user_id}/{sanitized_filename}"

            # Get blob
            blob = self.bucket.blob(gcs_path)

            # Check if exists
            if not blob.exists():
                raise StandardHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="File not found",
                    success=False,
                    data=None,
                )

            # Download content
            content = blob.download_as_bytes()
            content_type = blob.content_type or "application/octet-stream"

            logger.info(f"Downloaded file for user {user_id}: {gcs_path}")

            return content, content_type

        except HTTPException:
            raise
        except GoogleCloudError as e:
            logger.error(f"GCS error downloading file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to download file from cloud storage. Please try again.",
                success=False,
                data=None,
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to download file. Please try again.",
                success=False,
                data=None,
            )

    def delete_file(self, user_id: int, filename: str) -> bool:
        """
        Delete file from GCS.

        Args:
            user_id: User ID
            filename: Filename to delete

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            # Sanitize filename
            sanitized_filename = self._sanitize_filename(filename)

            # Create GCS path
            gcs_path = f"{user_id}/{sanitized_filename}"

            # Get blob
            blob = self.bucket.blob(gcs_path)

            # Delete if exists
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted file for user {user_id}: {gcs_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {gcs_path}")
                return False

        except GoogleCloudError as e:
            logger.error(f"GCS error deleting file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete file from cloud storage. Please try again.",
                success=False,
                data=None,
            )
        except Exception as e:
            logger.error(f"Unexpected error deleting file for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to delete file. Please try again.",
                success=False,
                data=None,
            )

    def list_user_files(self, user_id: int) -> list[dict]:
        """
        List all files for a user.

        Args:
            user_id: User ID

        Returns:
            list: List of file metadata dicts with keys:
                - name: Filename
                - gcs_path: Full GCS path
                - size: File size in bytes
                - content_type: MIME type
                - uploaded_at: ISO timestamp
                - purpose: File purpose from metadata

        Raises:
            HTTPException: If listing fails
        """
        try:
            # List blobs with user_id prefix
            prefix = f"{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)

            files = []
            for blob in blobs:
                # Extract metadata
                metadata = blob.metadata or {}

                files.append(
                    {
                        "name": blob.name.split("/")[-1],  # Get filename from path
                        "gcs_path": blob.name,
                        "size": blob.size,
                        "content_type": blob.content_type or "application/octet-stream",
                        "uploaded_at": metadata.get("upload_date", blob.time_created.isoformat()),
                        "purpose": metadata.get("purpose", "unknown"),
                    }
                )

            logger.info(f"Listed {len(files)} files for user {user_id}")
            return files

        except GoogleCloudError as e:
            logger.error(f"GCS error listing files for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to list files from cloud storage. Please try again.",
                success=False,
                data=None,
            )
        except Exception as e:
            logger.error(f"Unexpected error listing files for user {user_id}: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to list files. Please try again.",
                success=False,
                data=None,
            )

    def file_exists(self, user_id: int, filename: str) -> bool:
        """
        Check if file exists in GCS.

        Args:
            user_id: User ID
            filename: Filename to check

        Returns:
            bool: True if file exists
        """
        try:
            # Sanitize filename
            sanitized_filename = self._sanitize_filename(filename)

            # Create GCS path
            gcs_path = f"{user_id}/{sanitized_filename}"

            # Check if blob exists
            blob = self.bucket.blob(gcs_path)
            return blob.exists()

        except Exception as e:
            logger.error(f"Error checking file existence for user {user_id}: {e}")
            return False
