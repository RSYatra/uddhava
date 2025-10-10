"""
OpenAPI schema customization for enhanced Swagger UI documentation.

This module provides custom OpenAPI schema modifications to improve the
developer experience in Swagger UI, particularly for multipart/form-data
endpoints where FastAPI's default schema generation doesn't always provide
optimal examples.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def get_custom_openapi(app: FastAPI):
    """
    Generate custom OpenAPI schema with enhanced examples for form fields.

    This function modifies the auto-generated OpenAPI schema to inject realistic
    examples into form fields, replacing the generic "stringstri" placeholders
    that Swagger UI shows for multipart/form-data endpoints.

    Args:
        app: FastAPI application instance

    Returns:
        dict: Modified OpenAPI schema with enhanced examples

    Note:
        This is called once per application startup and the result is cached.
        The examples are injected into the components/schemas section where
        FastAPI defines the actual field properties.
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Enhance complete-profile endpoint with realistic examples
    _add_complete_profile_examples(openapi_schema)

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _add_complete_profile_examples(openapi_schema: dict) -> None:
    """
    Add realistic examples to the complete-profile endpoint schema.

    Args:
        openapi_schema: The OpenAPI schema dictionary to modify
    """
    # Navigate to the component schema (FastAPI uses $ref to point here)
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})

    # FastAPI auto-generates schema names with Body_ prefix
    schema_name = "Body_complete_devotee_profile_api_v1_auth_complete_profile_post"

    if schema_name not in schemas:
        return

    properties = schemas[schema_name].get("properties", {})

    # Define realistic examples for each field
    # These replace the generic "stringstri" placeholders in Swagger UI
    field_examples = {
        # Required fields
        "date_of_birth": "1990-05-15",
        "gender": "M",
        "marital_status": "MARRIED",
        "country_code": "+91",
        "mobile_number": "9876543210",
        "father_name": "Ram Kumar Sharma",
        "mother_name": "Sita Sharma",
        # Optional family fields
        "spouse_name": "Radha Sharma",
        "date_of_marriage": "2015-06-20",
        "national_id": "ABCDE1234F",
        # Optional location fields
        "address": "123 Main Street, Apartment 4B",
        "city": "Mumbai",
        "state_province": "Maharashtra",
        "country": "India",
        "postal_code": "400001",
        # Optional spiritual fields
        "initiation_status": "HARINAM",
        "spiritual_master": "His Holiness Radhanath Swami",
        "initiation_date": "2018-08-15",
        "initiation_place": "Vrindavan, India",
        "spiritual_guide": "Prabhu Krishna Das",
        # Optional ISKCON journey fields
        "when_were_you_introduced_to_iskcon": "2010",
        "who_introduced_you_to_iskcon": "My friend Prashant",
        "which_iskcon_center_you_first_connected_to": "ISKCON Vrindavan",
        # Optional chanting fields
        "chanting_number_of_rounds": 16,
        "chanting_16_rounds_since": "2015-01-01",
        # Optional education fields
        "devotional_courses": "Bhakti Shastri, Bhakti Vaibhava",
    }

    # Inject examples into schema properties
    for field_name, example_value in field_examples.items():
        if field_name in properties:
            # Set example for Swagger UI display
            properties[field_name]["example"] = example_value

            # Only set default for non-file fields
            # File upload fields should NOT have default values as it causes validation errors
            field_type = properties[field_name].get("type")
            field_format = properties[field_name].get("format")
            is_file_field = (
                field_format == "binary" or field_type == "string" and "file" in field_name.lower()
            )

            if not is_file_field and "default" not in properties[field_name]:
                properties[field_name]["default"] = example_value
