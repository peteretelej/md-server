"""
Sync API wrappers for async converter methods.
"""

import asyncio
import threading
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_thread_local = threading.local()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create an event loop in a thread-safe manner."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need a new one for sync operations
            if not hasattr(_thread_local, "loop"):
                _thread_local.loop = asyncio.new_event_loop()
            return _thread_local.loop
        return loop
    except RuntimeError:
        # No event loop in current thread
        if not hasattr(_thread_local, "loop"):
            _thread_local.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_thread_local.loop)
        return _thread_local.loop


def sync_wrapper(async_func: F) -> F:
    """
    Decorator to create sync version of async method.

    Handles thread-safe event loop management and proper cleanup.
    """

    @wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = get_or_create_event_loop()

        if loop.is_running():
            # Running in an existing async context
            # Use run_in_executor to avoid blocking
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(async_func(*args, **kwargs))
                )
                return future.result()
        else:
            # No running loop, safe to use run_until_complete
            return loop.run_until_complete(async_func(*args, **kwargs))

    return wrapper


class SyncConverterMixin:
    """Mixin providing sync versions of async converter methods."""

    def convert_file_sync(self, file_path, **options):
        """Synchronous version of convert_file."""
        return sync_wrapper(self.convert_file)(file_path, **options)

    def convert_url_sync(self, url, **options):
        """Synchronous version of convert_url."""
        return sync_wrapper(self.convert_url)(url, **options)

    def convert_content_sync(self, content, **options):
        """Synchronous version of convert_content."""
        return sync_wrapper(self.convert_content)(content, **options)

    def convert_text_sync(self, text, mime_type, **options):
        """Synchronous version of convert_text."""
        return sync_wrapper(self.convert_text)(text, mime_type, **options)
