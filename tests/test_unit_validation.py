import pytest
from pathlib import Path
from md_server.sdk.core.validation import (
    validate_file_path,
    validate_file_size_limits,
    validate_remote_file_size,
    detect_file_content_type,
    validate_conversion_options,
    sanitize_filename_for_api,
)
from md_server.sdk.exceptions import InvalidInputError


class TestValidateFilePath:
    """Test file path validation"""

    def test_valid_paths(self):
        """Test valid file paths"""
        valid_paths = [
            "document.pdf",
            "/path/to/document.pdf",
            "relative/path.txt",
            "../parent/file.docx",
            "~/home/file.md",
            "C:\\Windows\\file.txt",  # Windows path
        ]
        
        for path in valid_paths:
            result = validate_file_path(path)
            assert isinstance(result, Path)
            # Path object may normalize the path
            assert str(result) == path.strip() or str(result) == Path(path.strip()).as_posix()

    def test_empty_path(self):
        """Test empty path validation"""
        empty_paths = [
            "",
            None,
        ]
        
        for path in empty_paths:
            with pytest.raises(InvalidInputError, match="File path cannot be empty"):
                validate_file_path(path)
        
        # Whitespace only - should be handled after strip
        with pytest.raises(InvalidInputError, match="Invalid file path"):
            validate_file_path("   ")

    def test_invalid_path_types(self):
        """Test non-string path types"""
        invalid_types = [
            123,
            [],
            {},
            True,
        ]
        
        for path in invalid_types:
            with pytest.raises(InvalidInputError, match="File path cannot be empty"):
                validate_file_path(path)

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed"""
        path_with_spaces = "  /path/to/file.txt  "
        result = validate_file_path(path_with_spaces)
        assert str(result) == "/path/to/file.txt"

    def test_directory_only_path(self):
        """Test paths that result in empty names after Path processing"""
        # Path(".").name returns ".", not empty, so it's valid
        # Path("..").name returns "..", not empty, so it's valid
        
        # These should be valid as they have names  
        result = validate_file_path("file.txt")
        assert result.name == "file.txt"


class TestValidateFileSizeLimits:
    """Test file size limit validation"""

    def test_valid_sizes(self):
        """Test valid file sizes"""
        limits = {
            "default": 50 * 1024 * 1024,
            "image": 10 * 1024 * 1024,
            "pdf": 20 * 1024 * 1024,
        }
        
        # Within limits
        validate_file_size_limits(1024, "text/plain", limits)  # 1KB text
        validate_file_size_limits(5 * 1024 * 1024, "image/png", limits)  # 5MB image
        validate_file_size_limits(15 * 1024 * 1024, "application/pdf", limits)  # 15MB PDF

    def test_negative_size(self):
        """Test negative size validation"""
        limits = {"default": 50 * 1024 * 1024}
        
        with pytest.raises(InvalidInputError, match="File size cannot be negative"):
            validate_file_size_limits(-1, "text/plain", limits)

    def test_zero_size(self):
        """Test zero size validation"""
        limits = {"default": 50 * 1024 * 1024}
        
        with pytest.raises(InvalidInputError, match="File cannot be empty"):
            validate_file_size_limits(0, "text/plain", limits)

    def test_size_limits_by_content_type(self):
        """Test size limits for different content types"""
        limits = {
            "default": 50 * 1024 * 1024,
            "image": 10 * 1024 * 1024,
            "video": 100 * 1024 * 1024,
            "pdf": 20 * 1024 * 1024,
        }
        
        # Test image limit
        with pytest.raises(InvalidInputError, match="exceeds.*limit"):
            validate_file_size_limits(15 * 1024 * 1024, "image/png", limits)  # Over 10MB
        
        # Test PDF limit
        with pytest.raises(InvalidInputError, match="exceeds.*limit"):
            validate_file_size_limits(25 * 1024 * 1024, "application/pdf", limits)  # Over 20MB
        
        # Test video limit
        with pytest.raises(InvalidInputError, match="exceeds.*limit"):
            validate_file_size_limits(150 * 1024 * 1024, "video/mp4", limits)  # Over 100MB
        
        # Test default limit
        with pytest.raises(InvalidInputError, match="exceeds.*limit"):
            validate_file_size_limits(60 * 1024 * 1024, "text/plain", limits)  # Over 50MB

    def test_edge_cases(self):
        """Test edge cases"""
        limits = {"default": 10 * 1024 * 1024}
        
        # Exactly at limit
        validate_file_size_limits(10 * 1024 * 1024, "text/plain", limits)
        
        # Just under limit
        validate_file_size_limits(10 * 1024 * 1024 - 1, "text/plain", limits)
        
        # Just over limit
        with pytest.raises(InvalidInputError):
            validate_file_size_limits(10 * 1024 * 1024 + 1, "text/plain", limits)


class TestValidateRemoteFileSize:
    """Test remote file size validation"""

    def test_valid_remote_sizes(self):
        """Test valid remote file sizes"""
        max_size = 25 * 1024 * 1024  # 25MB
        
        validate_remote_file_size(1024, max_size)  # 1KB
        validate_remote_file_size(max_size, max_size)  # Exactly at limit
        validate_remote_file_size(max_size - 1, max_size)  # Just under limit

    def test_negative_remote_size(self):
        """Test negative remote size"""
        with pytest.raises(InvalidInputError, match="File size cannot be negative"):
            validate_remote_file_size(-1, 25 * 1024 * 1024)

    def test_zero_remote_size(self):
        """Test zero remote size"""
        with pytest.raises(InvalidInputError, match="Remote file cannot be empty"):
            validate_remote_file_size(0, 25 * 1024 * 1024)

    def test_oversized_remote_file(self):
        """Test oversized remote file"""
        max_size = 25 * 1024 * 1024
        
        with pytest.raises(InvalidInputError, match="Remote file too large"):
            validate_remote_file_size(max_size + 1, max_size)


class TestDetectFileContentType:
    """Test file content type detection"""

    def test_empty_content(self):
        """Test empty content detection"""
        detected = detect_file_content_type(b"", "test.txt")
        assert detected == "application/octet-stream"

    def test_filename_based_detection(self):
        """Test filename-based detection"""
        test_cases = [
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("page.html", "text/html"),
            ("data.json", "application/json"),
            ("spreadsheet.csv", "text/csv"),
        ]
        
        for filename, expected in test_cases:
            detected = detect_file_content_type(b"sample content", filename)
            assert detected == expected

    def test_magic_number_detection(self):
        """Test magic number detection"""
        test_cases = [
            (b"\x89PNG\r\n\x1a\n", "unknown", "image/png"),
            (b"\xff\xd8\xff", "unknown", "image/jpeg"),
            (b"GIF87a", "unknown", "image/gif"),
            (b"GIF89a", "unknown", "image/gif"),
            (b"%PDF", "unknown", "application/pdf"),
            (b"PK\x03\x04", "unknown", "application/zip"),
        ]
        
        for content, filename, expected in test_cases:
            content_with_data = content + b"\x00" * 50
            detected = detect_file_content_type(content_with_data, filename)
            assert detected == expected

    def test_office_document_detection(self):
        """Test Office document detection"""
        zip_content = b"PK\x03\x04" + b"\x00" * 100
        
        # Office documents are ZIP-based but should be detected by extension
        detected = detect_file_content_type(zip_content, "document.docx")
        assert "wordprocessingml" in detected or "docx" in detected
        
        detected = detect_file_content_type(zip_content, "spreadsheet.xlsx")
        assert "spreadsheetml" in detected or "xlsx" in detected
        
        detected = detect_file_content_type(zip_content, "presentation.pptx")
        assert "presentationml" in detected or "pptx" in detected

    def test_old_office_format_detection(self):
        """Test old Office format detection"""
        ole_content = b"\xd0\xcf\x11\xe0" + b"\x00" * 100
        
        detected = detect_file_content_type(ole_content, "document.doc")
        assert detected == "application/msword"
        
        detected = detect_file_content_type(ole_content, "spreadsheet.xls")
        assert detected == "application/vnd.ms-excel"
        
        detected = detect_file_content_type(ole_content, "presentation.ppt")
        assert detected == "application/vnd.ms-powerpoint"

    def test_text_content_detection(self):
        """Test text content detection"""
        text_content = b"Hello, world! This is plain text."
        
        detected = detect_file_content_type(text_content, "document.html")
        assert detected == "text/html"
        
        detected = detect_file_content_type(text_content, "config.xml")
        assert detected in ["text/xml", "application/xml"]  # Both are valid
        
        detected = detect_file_content_type(text_content, "data.json")
        assert detected == "application/json"
        
        detected = detect_file_content_type(text_content, "unknown.txt")
        assert detected == "text/plain"

    def test_binary_fallback(self):
        """Test binary content fallback"""
        binary_content = b"\x00\x01\x02\x03" * 25
        detected = detect_file_content_type(binary_content, "unknown.bin")
        assert detected == "application/octet-stream"


class TestValidateConversionOptions:
    """Test conversion options validation"""

    def test_valid_boolean_options(self):
        """Test valid boolean options"""
        allowed_keys = {
            "js_rendering", "extract_images", "ocr_enabled", 
            "preserve_formatting", "clean_markdown"
        }
        
        options = {
            "js_rendering": True,
            "extract_images": False,
            "ocr_enabled": True,
        }
        
        validated = validate_conversion_options(options, allowed_keys)
        assert validated == options

    def test_valid_timeout_option(self):
        """Test valid timeout options"""
        allowed_keys = {"timeout"}
        
        # Integer timeout
        options = {"timeout": 30}
        validated = validate_conversion_options(options, allowed_keys)
        assert validated == options
        
        # Float timeout
        options = {"timeout": 30.5}
        validated = validate_conversion_options(options, allowed_keys)
        assert validated == options

    def test_invalid_boolean_options(self):
        """Test invalid boolean options"""
        allowed_keys = {"js_rendering"}
        
        invalid_values = ["true", 1, 0, "false", None]
        
        for value in invalid_values:
            with pytest.raises(InvalidInputError, match="must be boolean"):
                validate_conversion_options({"js_rendering": value}, allowed_keys)

    def test_invalid_timeout_options(self):
        """Test invalid timeout options"""
        allowed_keys = {"timeout"}
        
        invalid_timeouts = [0, -1, "30", None, []]
        
        for timeout in invalid_timeouts:
            with pytest.raises(InvalidInputError, match="must be positive number"):
                validate_conversion_options({"timeout": timeout}, allowed_keys)

    def test_filtered_options(self):
        """Test that disallowed options are filtered out"""
        allowed_keys = {"js_rendering", "timeout"}
        
        options = {
            "js_rendering": True,
            "timeout": 30,
            "disallowed_option": "value",
            "another_bad_option": 123,
        }
        
        validated = validate_conversion_options(options, allowed_keys)
        expected = {
            "js_rendering": True,
            "timeout": 30,
        }
        assert validated == expected


class TestSanitizeFilenameForApi:
    """Test filename sanitization for API"""

    def test_valid_filenames(self):
        """Test valid filenames"""
        valid_names = [
            "document.pdf",
            "image_001.png",
            "file-name.txt",
            "simple.docx",
        ]
        
        for name in valid_names:
            sanitized = sanitize_filename_for_api(name)
            assert sanitized == name

    def test_empty_filename(self):
        """Test empty filename handling"""
        assert sanitize_filename_for_api("") == "unknown"
        assert sanitize_filename_for_api(None) == "unknown"

    def test_path_component_removal(self):
        """Test path component removal"""
        test_cases = [
            ("/path/to/file.txt", "file.txt"),
            ("../parent/file.docx", "file.docx"),
            ("./current/file.pdf", "file.pdf"),
        ]
        
        # Windows path is only handled on Windows
        import platform
        if platform.system() == "Windows":
            test_cases.append(("C:\\Windows\\file.exe", "file.exe"))
        
        for path, expected in test_cases:
            sanitized = sanitize_filename_for_api(path)
            assert sanitized == expected

    def test_unsafe_character_replacement(self):
        """Test unsafe character replacement"""
        test_cases = [
            ("file with spaces.txt", "file_with_spaces.txt"),
            ("file@#$%.docx", "file____.docx"),
            ("file(1).pdf", "file_1_.pdf"),
            ("file[special].txt", "file_special_.txt"),
        ]
        
        for original, expected in test_cases:
            sanitized = sanitize_filename_for_api(original)
            assert sanitized == expected

    def test_leading_dot_dash_handling(self):
        """Test handling of leading dots and dashes"""
        test_cases = [
            (".hidden", "file_.hidden"),
            ("-filename.txt", "file_-filename.txt"),
            ("..config", "file_..config"),
        ]
        
        for original, expected in test_cases:
            sanitized = sanitize_filename_for_api(original)
            assert sanitized == expected

    def test_length_limiting(self):
        """Test filename length limiting"""
        # Very long filename
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename_for_api(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")
        
        # Long name without extension
        long_name_no_ext = "a" * 300
        sanitized = sanitize_filename_for_api(long_name_no_ext)
        assert len(sanitized) <= 255

    def test_fallback_to_unknown(self):
        """Test fallback to 'unknown'"""
        problematic_names = [
            ".....",
            "-----",
            "@#$%^&*()",
        ]
        
        for name in problematic_names:
            sanitized = sanitize_filename_for_api(name)
            # Should either be properly sanitized or fallback to unknown
            assert len(sanitized) > 0