import sys
from contextlib import contextmanager
from typing import Any, Generator, Optional, Type
from unittest.mock import patch, MagicMock


@contextmanager
def inject_import_error(
    module_name: str, error_message: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager that forces ImportError for specified module."""
    if error_message is None:
        error_message = f"No module named '{module_name}'"

    original_import = __builtins__["__import__"]

    def mock_import(name, *args, **kwargs):
        if name == module_name or name.startswith(f"{module_name}."):
            raise ImportError(error_message)
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        # Also clear from sys.modules if already loaded
        modules_to_remove = [
            mod
            for mod in sys.modules.keys()
            if mod == module_name or mod.startswith(f"{module_name}.")
        ]
        removed_modules = {}

        for mod in modules_to_remove:
            removed_modules[mod] = sys.modules.pop(mod, None)

        try:
            yield
        finally:
            # Restore removed modules
            for mod, value in removed_modules.items():
                if value is not None:
                    sys.modules[mod] = value


@contextmanager
def inject_exception(
    target: str,
    exception_type: Type[Exception] = Exception,
    message: str = "Injected test exception",
    call_count: Optional[int] = None,
) -> Generator[None, None, None]:
    """Context manager that injects exceptions into function calls."""
    call_counter = {"count": 0}

    def exception_side_effect(*args, **kwargs):
        call_counter["count"] += 1
        if call_count is None or call_counter["count"] <= call_count:
            raise exception_type(message)
        # After call_count exceeded, call the original
        return MagicMock()

    with patch(target, side_effect=exception_side_effect):
        yield


@contextmanager
def inject_attribute_error(
    target_object: Any, attribute_name: str, error_message: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager that injects AttributeError when accessing an attribute."""
    if error_message is None:
        error_message = f"'{type(target_object).__name__}' object has no attribute '{attribute_name}'"

    original_getattr = getattr(target_object, "__getattribute__", None)

    def mock_getattribute(name):
        if name == attribute_name:
            raise AttributeError(error_message)
        if original_getattr:
            return original_getattr(name)
        return object.__getattribute__(target_object, name)

    with patch.object(target_object, "__getattribute__", mock_getattribute):
        yield


@contextmanager
def inject_file_not_found(
    file_path: str, error_message: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager that injects FileNotFoundError for specific file path."""
    if error_message is None:
        error_message = f"No such file or directory: '{file_path}'"

    original_open = open

    def mock_open(path, *args, **kwargs):
        if str(path) == file_path:
            raise FileNotFoundError(error_message)
        return original_open(path, *args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        yield


@contextmanager
def inject_permission_error(
    file_path: str, error_message: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager that injects PermissionError for specific file path."""
    if error_message is None:
        error_message = f"Permission denied: '{file_path}'"

    original_open = open

    def mock_open(path, *args, **kwargs):
        if str(path) == file_path:
            raise PermissionError(error_message)
        return original_open(path, *args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        yield


@contextmanager
def inject_memory_error(
    target: str, threshold_mb: int = 100
) -> Generator[None, None, None]:
    """Context manager that injects MemoryError when memory usage exceeds threshold."""

    def memory_check_side_effect(*args, **kwargs):
        # Simulate memory exhaustion
        raise MemoryError(f"Memory allocation failed (threshold: {threshold_mb}MB)")

    with patch(target, side_effect=memory_check_side_effect):
        yield


@contextmanager
def inject_timeout_error(
    target: str, timeout_seconds: float = 1.0
) -> Generator[None, None, None]:
    """Context manager that injects TimeoutError after specified duration."""
    import time

    def timeout_side_effect(*args, **kwargs):
        time.sleep(timeout_seconds + 0.1)  # Slightly longer than timeout
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")

    with patch(target, side_effect=timeout_side_effect):
        yield


@contextmanager
def inject_keyboard_interrupt(
    target: str, after_calls: int = 1
) -> Generator[None, None, None]:
    """Context manager that injects KeyboardInterrupt after specified number of calls."""
    call_counter = {"count": 0}

    def interrupt_side_effect(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] >= after_calls:
            raise KeyboardInterrupt("Test keyboard interrupt")
        return MagicMock()

    with patch(target, side_effect=interrupt_side_effect):
        yield


class ErrorInjector:
    """Utility class for systematic error injection in tests."""

    def __init__(self):
        self.active_patches = []

    def add_import_error(self, module_name: str, message: Optional[str] = None):
        """Add ImportError injection for module."""
        return inject_import_error(module_name, message)

    def add_exception(
        self,
        target: str,
        exception_type: Type[Exception] = Exception,
        message: str = "Test exception",
    ):
        """Add generic exception injection."""
        return inject_exception(target, exception_type, message)

    def add_file_error(self, file_path: str, error_type: str = "not_found"):
        """Add file-related error injection."""
        if error_type == "not_found":
            return inject_file_not_found(file_path)
        elif error_type == "permission":
            return inject_permission_error(file_path)
        else:
            raise ValueError(f"Unsupported file error type: {error_type}")

    def cleanup(self):
        """Clean up any active patches."""
        for patch_obj in self.active_patches:
            if hasattr(patch_obj, "stop"):
                patch_obj.stop()
        self.active_patches.clear()


# Convenience functions for common error scenarios
def simulate_missing_dependency(dependency: str):
    """Context manager for missing Python dependency."""
    return inject_import_error(dependency)


def simulate_file_system_error(file_path: str, error_type: str = "not_found"):
    """Context manager for file system errors."""
    injector = ErrorInjector()
    return injector.add_file_error(file_path, error_type)


def simulate_resource_exhaustion(target: str, resource_type: str = "memory"):
    """Context manager for resource exhaustion errors."""
    if resource_type == "memory":
        return inject_memory_error(target)
    elif resource_type == "timeout":
        return inject_timeout_error(target)
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")


def simulate_user_interruption(target: str, after_calls: int = 1):
    """Context manager for user interruption (Ctrl+C)."""
    return inject_keyboard_interrupt(target, after_calls)
