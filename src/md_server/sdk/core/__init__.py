"""
Core pure functions for the SDK.

This package contains I/O-free functions for remote operations,
sync wrappers, and validation.
"""

from .remote import (
    build_file_payload,
    build_url_payload,
    build_content_payload,
    build_text_payload,
    parse_conversion_response,
    validate_api_response,
    extract_error_details,
    merge_request_options,
    encode_file_content,
    map_status_code_to_exception,
    parse_http_error_response,
)

from .utils import (
    build_auth_headers,
    should_retry_request,
    calculate_retry_delay,
    classify_request_exception,
)

from .local_converter import (
    validate_local_file_input,
    validate_local_content_input,
    validate_local_text_input,
    build_conversion_options,
    create_conversion_metadata,
    create_conversion_result,
    classify_conversion_error,
    extract_url_options,
    merge_conversion_options,
    validate_conversion_response,
    calculate_processing_metrics,
)

from .sync import (
    detect_event_loop_state,
    create_thread_local_loop,
    run_in_thread_pool,
    validate_sync_conversion_args,
    wrap_async_result,
    handle_sync_conversion_error,
)

from .validation import (
    validate_file_path,
    validate_file_size_limits,
    validate_remote_file_size,
    detect_file_content_type,
    validate_conversion_options,
    sanitize_filename_for_api,
)

__all__ = [
    # Remote functions
    "build_file_payload",
    "build_url_payload",
    "build_content_payload",
    "build_text_payload",
    "parse_conversion_response",
    "validate_api_response",
    "extract_error_details",
    "merge_request_options",
    "build_auth_headers",
    "encode_file_content",
    "map_status_code_to_exception",
    "parse_http_error_response",
    "should_retry_request",
    "calculate_retry_delay",
    "classify_request_exception",
    # Local converter functions
    "validate_local_file_input",
    "validate_local_content_input",
    "validate_local_text_input",
    "build_conversion_options",
    "create_conversion_metadata",
    "create_conversion_result",
    "classify_conversion_error",
    "extract_url_options",
    "merge_conversion_options",
    "validate_conversion_response",
    "calculate_processing_metrics",
    # Sync functions
    "detect_event_loop_state",
    "create_thread_local_loop",
    "run_in_thread_pool",
    "validate_sync_conversion_args",
    "wrap_async_result",
    "handle_sync_conversion_error",
    # Validation functions
    "validate_file_path",
    "validate_file_size_limits",
    "validate_remote_file_size",
    "detect_file_content_type",
    "validate_conversion_options",
    "sanitize_filename_for_api",
]
