"""
Sync API wrappers for async converter methods.
"""

import asyncio
import threading
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .core.sync import (
    detect_event_loop_state,
    create_thread_local_loop,
    run_in_thread_pool,
)

F = TypeVar("F", bound=Callable[..., Any])

_thread_local = threading.local()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create an event loop in a thread-safe manner."""
    loop_state = detect_event_loop_state()

    if loop_state == "running":
        # If loop is running, we need a new one for sync operations
        if not hasattr(_thread_local, "loop"):
            _thread_local.loop = create_thread_local_loop()
        return cast(asyncio.AbstractEventLoop, _thread_local.loop)
    elif loop_state == "stopped":
        # Use existing stopped loop
        return asyncio.get_event_loop()
    else:
        # No event loop in current thread
        if not hasattr(_thread_local, "loop"):
            _thread_local.loop = create_thread_local_loop()
            asyncio.set_event_loop(_thread_local.loop)
        return cast(asyncio.AbstractEventLoop, _thread_local.loop)


def sync_wrapper(async_func: F) -> F:
    """
    Decorator to create sync version of async method.

    Handles thread-safe event loop management and proper cleanup.
    """

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop_state = detect_event_loop_state()

        if loop_state == "running":
            # Running in an existing async context
            # Use thread pool to avoid blocking
            return run_in_thread_pool(async_func(*args, **kwargs))
        else:
            # No running loop, safe to use run_until_complete
            loop = get_or_create_event_loop()
            return loop.run_until_complete(async_func(*args, **kwargs))

    return cast(F, wrapper)


class SyncConverterMixin:
    """Mixin providing sync versions of async converter methods."""

    def convert_file_sync(self, file_path: str, **options: Any) -> Any:
        """Synchronous version of convert_file."""
        return sync_wrapper(getattr(self, "convert_file"))(file_path, **options)

    def convert_url_sync(self, url: str, **options: Any) -> Any:
        """Synchronous version of convert_url."""
        return sync_wrapper(getattr(self, "convert_url"))(url, **options)

    def convert_content_sync(self, content: bytes, **options: Any) -> Any:
        """Synchronous version of convert_content."""
        return sync_wrapper(getattr(self, "convert_content"))(content, **options)

    def convert_text_sync(self, text: str, mime_type: str, **options: Any) -> Any:
        """Synchronous version of convert_text."""
        return sync_wrapper(getattr(self, "convert_text"))(text, mime_type, **options)
