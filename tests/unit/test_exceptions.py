import pytest
from md_server.core.exceptions import (
    MarkdownConversionError,
    UnsupportedFileTypeError,
    FileTooLargeError,
    URLFetchError,
    ConversionTimeoutError
)


class TestMarkdownConversionError:
    def test_is_exception(self):
        assert issubclass(MarkdownConversionError, Exception)

    def test_can_be_raised_with_message(self):
        with pytest.raises(MarkdownConversionError) as exc_info:
            raise MarkdownConversionError("test error message")
        
        assert str(exc_info.value) == "test error message"

    def test_can_be_raised_without_message(self):
        with pytest.raises(MarkdownConversionError):
            raise MarkdownConversionError()


class TestUnsupportedFileTypeError:
    def test_inherits_from_markdown_conversion_error(self):
        assert issubclass(UnsupportedFileTypeError, MarkdownConversionError)

    def test_can_be_raised_with_message(self):
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            raise UnsupportedFileTypeError("Unsupported file type: .xyz")
        
        assert str(exc_info.value) == "Unsupported file type: .xyz"

    def test_can_be_caught_as_markdown_conversion_error(self):
        with pytest.raises(MarkdownConversionError):
            raise UnsupportedFileTypeError("test")


class TestFileTooLargeError:
    def test_inherits_from_markdown_conversion_error(self):
        assert issubclass(FileTooLargeError, MarkdownConversionError)

    def test_can_be_raised_with_message(self):
        with pytest.raises(FileTooLargeError) as exc_info:
            raise FileTooLargeError("File size exceeds 50MB limit")
        
        assert str(exc_info.value) == "File size exceeds 50MB limit"

    def test_can_be_caught_as_markdown_conversion_error(self):
        with pytest.raises(MarkdownConversionError):
            raise FileTooLargeError("test")


class TestURLFetchError:
    def test_inherits_from_markdown_conversion_error(self):
        assert issubclass(URLFetchError, MarkdownConversionError)

    def test_can_be_raised_with_message(self):
        with pytest.raises(URLFetchError) as exc_info:
            raise URLFetchError("Failed to fetch URL: https://example.com")
        
        assert str(exc_info.value) == "Failed to fetch URL: https://example.com"

    def test_can_be_caught_as_markdown_conversion_error(self):
        with pytest.raises(MarkdownConversionError):
            raise URLFetchError("test")


class TestConversionTimeoutError:
    def test_inherits_from_markdown_conversion_error(self):
        assert issubclass(ConversionTimeoutError, MarkdownConversionError)

    def test_can_be_raised_with_message(self):
        with pytest.raises(ConversionTimeoutError) as exc_info:
            raise ConversionTimeoutError("Conversion timed out after 30s")
        
        assert str(exc_info.value) == "Conversion timed out after 30s"

    def test_can_be_caught_as_markdown_conversion_error(self):
        with pytest.raises(MarkdownConversionError):
            raise ConversionTimeoutError("test")


class TestExceptionInheritance:
    def test_all_custom_exceptions_inherit_from_base(self):
        custom_exceptions = [
            UnsupportedFileTypeError,
            FileTooLargeError,
            URLFetchError,
            ConversionTimeoutError
        ]
        
        for exc_class in custom_exceptions:
            assert issubclass(exc_class, MarkdownConversionError)
            assert issubclass(exc_class, Exception)

    def test_exception_hierarchy_with_multiple_inheritance(self):
        try:
            raise ConversionTimeoutError("timeout")
        except MarkdownConversionError:
            pass
        except Exception:
            pytest.fail("Should have been caught as MarkdownConversionError")

    def test_exception_messages_preserved(self):
        test_message = "Custom error message with details"
        
        exceptions_to_test = [
            MarkdownConversionError(test_message),
            UnsupportedFileTypeError(test_message),
            FileTooLargeError(test_message),
            URLFetchError(test_message),
            ConversionTimeoutError(test_message)
        ]
        
        for exc in exceptions_to_test:
            assert str(exc) == test_message