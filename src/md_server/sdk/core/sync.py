"""
Pure functions for sync wrapper operations.

Functions for event loop detection, thread management, and async-to-sync
conversion without I/O dependencies.
"""

import asyncio
import concurrent.futures
from typing import Any, Dict


def detect_event_loop_state() -> str:
    """Detect current event loop state.

    Returns:
        - "none": No event loop in current thread
        - "running": Event loop exists and is running
        - "stopped": Event loop exists but not running
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return "running"
        else:
            return "stopped"
    except RuntimeError:
        return "none"


def create_thread_local_loop() -> asyncio.AbstractEventLoop:
    """Create a new event loop for thread-local use."""
    return asyncio.new_event_loop()


def run_in_thread_pool(coro: Any, timeout: int = 30) -> Any:
    """Run coroutine in thread pool executor."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: asyncio.run(coro))
        return future.result(timeout=timeout)


def validate_sync_conversion_args(**kwargs) -> Dict[str, Any]:
    """Validate and filter arguments for sync conversion."""
    valid_args = {}

    allowed_keys = {
        "js_rendering",
        "extract_images",
        "ocr_enabled",
        "preserve_formatting",
        "clean_markdown",
        "timeout",
    }

    for key, value in kwargs.items():
        if key in allowed_keys and value is not None:
            valid_args[key] = value

    return valid_args


def wrap_async_result(result: Any) -> Any:
    """Wrap async result for sync consumption."""
    return result


def handle_sync_conversion_error(error: Exception) -> Exception:
    """Convert async errors to appropriate sync errors."""
    return error
