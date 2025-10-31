"""
Error handling utilities for better user feedback and debugging.
"""

from typing import Dict, Any, Optional
from flask import jsonify
import traceback
import logging

logger = logging.getLogger(__name__)


class ErrorCategory:
    """Error categories for better error handling."""
    USER_ERROR = "user_error"  # User can fix (invalid input, missing data)
    SYSTEM_ERROR = "system_error"  # System issue (API failure, network)
    CRITICAL_ERROR = "critical_error"  # Unexpected failure (needs investigation)


class AppError(Exception):
    """Custom application error with category and user-friendly message."""
    
    def __init__(
        self,
        message: str,
        category: str = ErrorCategory.SYSTEM_ERROR,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        status_code: int = 500
    ):
        self.message = message
        self.category = category
        self.details = details
        self.suggestion = suggestion
        self.status_code = status_code
        super().__init__(self.message)


def create_error_response(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error: The exception that occurred
        include_traceback: Whether to include full traceback (for debugging)
    
    Returns:
        Dictionary with error details
    """
    if isinstance(error, AppError):
        response = {
            "error": error.message,
            "category": error.category,
            "status_code": error.status_code
        }
        if error.details:
            response["details"] = error.details
        if error.suggestion:
            response["suggestion"] = error.suggestion
        if include_traceback:
            response["traceback"] = traceback.format_exc()
        return response
    
    # Generic error handling
    error_type = type(error).__name__
    error_message = str(error)
    
    # Classify generic errors
    if "FileNotFoundError" in error_type or "file" in error_message.lower():
        category = ErrorCategory.USER_ERROR
        suggestion = "Please check that the file exists and the path is correct."
    elif "KeyError" in error_type or "missing" in error_message.lower():
        category = ErrorCategory.USER_ERROR
        suggestion = "Please check that all required fields are provided."
    elif "ConnectionError" in error_type or "timeout" in error_message.lower():
        category = ErrorCategory.SYSTEM_ERROR
        suggestion = "Network issue detected. Please try again in a moment."
    elif "APIError" in error_type or "api" in error_message.lower():
        category = ErrorCategory.SYSTEM_ERROR
        suggestion = "API service issue. Please check your API key and try again."
    else:
        category = ErrorCategory.CRITICAL_ERROR
        suggestion = "An unexpected error occurred. Please contact support if this persists."
    
    response = {
        "error": error_message,
        "category": category,
        "error_type": error_type,
        "suggestion": suggestion
    }
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response


def handle_api_error(error: Exception, include_traceback: bool = False):
    """
    Handle API errors and return JSON response.
    
    Args:
        error: The exception that occurred
        include_traceback: Whether to include traceback
    
    Returns:
        Flask JSON response with error details
    """
    logger.error(f"API Error: {error}", exc_info=True)
    
    error_response = create_error_response(error, include_traceback)
    
    status_code = error_response.get("status_code", 500)
    if isinstance(error, AppError):
        status_code = error.status_code
    
    return jsonify(error_response), status_code


def validate_file_upload(file, allowed_extensions: tuple = ('.csv', '.xlsx', '.xls'), max_size_mb: int = 50):
    """
    Validate file upload.
    
    Args:
        file: File object from Flask request
        allowed_extensions: Tuple of allowed file extensions
        max_size_mb: Maximum file size in MB
    
    Returns:
        None if valid, raises AppError if invalid
    """
    if not file or file.filename == "":
        raise AppError(
            "No file uploaded",
            category=ErrorCategory.USER_ERROR,
            suggestion="Please select a file to upload.",
            status_code=400
        )
    
    if not file.filename.lower().endswith(allowed_extensions):
        raise AppError(
            f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}",
            category=ErrorCategory.USER_ERROR,
            suggestion=f"Please upload a file with one of these extensions: {', '.join(allowed_extensions)}",
            status_code=400
        )
    
    # Check file size (Flask's file object has a size attribute)
    file_size_mb = len(file.read()) / (1024 * 1024)
    file.seek(0)  # Reset file pointer
    
    if file_size_mb > max_size_mb:
        raise AppError(
            f"File too large. Maximum size: {max_size_mb}MB",
            category=ErrorCategory.USER_ERROR,
            suggestion=f"Please upload a file smaller than {max_size_mb}MB",
            status_code=400
        )


def validate_required_fields(data: Dict[str, Any], required_fields: list):
    """
    Validate that required fields are present.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
    
    Returns:
        None if valid, raises AppError if invalid
    """
    missing = [field for field in required_fields if field not in data or not data[field]]
    
    if missing:
        raise AppError(
            f"Missing required fields: {', '.join(missing)}",
            category=ErrorCategory.USER_ERROR,
            suggestion=f"Please provide: {', '.join(missing)}",
            status_code=400
        )


def validate_site_config(site_name: str = None, site_url: str = None, username: str = None, password: str = None):
    """
    Validate site configuration.
    
    Args:
        site_name: Site name from config
        site_url: Site URL
        username: WordPress username
        password: WordPress password
    
    Returns:
        None if valid, raises AppError if invalid
    """
    if not site_name and not (site_url and username and password):
        raise AppError(
            "Site configuration incomplete",
            category=ErrorCategory.USER_ERROR,
            suggestion="Please provide either a site_name (from config) or site_url, username, and password.",
            status_code=400
        )
    
    if site_url and not site_url.startswith(('http://', 'https://')):
        raise AppError(
            "Invalid site URL format",
            category=ErrorCategory.USER_ERROR,
            suggestion="Site URL must start with http:// or https://",
            status_code=400
        )
