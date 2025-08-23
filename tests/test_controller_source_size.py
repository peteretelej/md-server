"""Test source size calculation functionality"""

import base64
import pytest
from md_server.core.error_mapper import calculate_source_size


class TestSourceSizeCalculation:
    """Test source size calculation for different input types"""
    
    @pytest.mark.parametrize("input_type,data,expected_size", [
        # URL inputs
        ("json_url", {"url": "https://example.com/test.pdf"}, 28),  # Correct byte count
        ("json_url", {"url": ""}, 0),
        ("json_url", {}, 0),
        
        # Text inputs
        ("json_text", {"text": "Hello world"}, 11),
        ("json_text_typed", {"text": "Hello 世界"}, 12),  # UTF-8 bytes
        ("json_text", {"text": ""}, 0),
        ("json_text", {}, 0),
        
        # Base64 content
        ("json_content", {"content": base64.b64encode(b"test content").decode()}, 12),
        ("json_content", {"content": "invalid base64 with spaces"}, 0),
        ("json_content", {"content": ""}, 0),
        ("json_content", {}, 0),
    ])
    def test_source_size_calculation(self, input_type, data, expected_size):
        """Test source size calculation for various input types and edge cases"""
        size = calculate_source_size(input_type, {}, data)
        assert size == expected_size
    
    def test_binary_content_fallback(self):
        """Test source size calculation falls back to content_data"""
        content = b"Binary file content"
        size = calculate_source_size("unknown_type", {"content": content}, {})
        assert size == len(content)
        
        # No content data fallback
        size = calculate_source_size("unknown_type", {}, {})
        assert size == 0