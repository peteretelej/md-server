import pytest
import logging
from unittest.mock import patch
from md_server.browser import BrowserChecker


class TestBrowserLogging:
    """Test browser availability logging"""

    @pytest.fixture
    def caplog_with_level(self, caplog):
        """Set logging level to capture all messages"""
        caplog.set_level(logging.INFO)
        return caplog

    def test_available_browser_logging_message(self, caplog_with_level):
        """Test logging message when browser is available"""
        BrowserChecker.log_availability(True)
        
        assert len(caplog_with_level.records) == 1
        record = caplog_with_level.records[0]
        
        assert record.levelname == "INFO"
        assert "URL Conversion: Using Crawl4AI with Playwright browsers" in record.message
        assert "JavaScript support enabled" in record.message

    def test_unavailable_browser_warning_message(self, caplog_with_level):
        """Test warning message when browser is unavailable"""
        BrowserChecker.log_availability(False)
        
        assert len(caplog_with_level.records) == 1
        record = caplog_with_level.records[0]
        
        assert record.levelname == "WARNING"
        assert "WARNING: URL Conversion: Playwright browsers not available" in record.message
        assert "using MarkItDown for basic URL conversions" in record.message
        assert "Install Playwright for Crawl4AI" in record.message

    def test_log_level_verification(self, caplog_with_level):
        """Test that log levels are set correctly"""
        # Test INFO level for available browser
        BrowserChecker.log_availability(True)
        assert caplog_with_level.records[0].levelno == logging.INFO
        
        caplog_with_level.clear()
        
        # Test WARNING level for unavailable browser  
        BrowserChecker.log_availability(False)
        assert caplog_with_level.records[0].levelno == logging.WARNING

    def test_log_message_content_accuracy(self, caplog_with_level):
        """Test accuracy of log message content"""
        # Test available message contains expected elements
        BrowserChecker.log_availability(True)
        message = caplog_with_level.records[0].message
        
        assert "URL Conversion" in message
        assert "Crawl4AI" in message
        assert "Playwright browsers" in message
        assert "JavaScript support enabled" in message
        
        caplog_with_level.clear()
        
        # Test unavailable message contains expected elements
        BrowserChecker.log_availability(False)
        message = caplog_with_level.records[0].message
        
        assert "WARNING" in message
        assert "URL Conversion" in message
        assert "Playwright browsers not available" in message
        assert "MarkItDown for basic URL conversions" in message
        assert "github.com/peteretelej/md-server" in message

    def test_no_duplicate_logging(self, caplog_with_level):
        """Test that log_availability doesn't create duplicate messages"""
        BrowserChecker.log_availability(True)
        assert len(caplog_with_level.records) == 1
        
        BrowserChecker.log_availability(False) 
        assert len(caplog_with_level.records) == 2
        
        # Verify messages are distinct
        assert caplog_with_level.records[0].levelname == "INFO"
        assert caplog_with_level.records[1].levelname == "WARNING"

    def test_logging_with_different_loggers(self, caplog_with_level):
        """Test logging works with different logger configurations"""
        # Set specific logger level
        logger = logging.getLogger("md_server.browser")
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        try:
            BrowserChecker.log_availability(True)
            assert len(caplog_with_level.records) == 1
            assert "JavaScript support enabled" in caplog_with_level.records[0].message
        finally:
            logger.setLevel(original_level)

    @pytest.mark.parametrize("available,expected_level,expected_content", [
        (True, "INFO", "Using Crawl4AI with Playwright browsers"),
        (False, "WARNING", "Playwright browsers not available"),
    ])
    def test_parametrized_logging(self, caplog_with_level, available, expected_level, expected_content):
        """Test logging with parametrized inputs"""
        BrowserChecker.log_availability(available)
        
        assert len(caplog_with_level.records) == 1
        record = caplog_with_level.records[0]
        assert record.levelname == expected_level
        assert expected_content in record.message

    def test_log_message_includes_github_link(self, caplog_with_level):
        """Test that unavailable message includes GitHub documentation link"""
        BrowserChecker.log_availability(False)
        
        record = caplog_with_level.records[0]
        assert "https://github.com/peteretelej/md-server" in record.message
        # Don't test fragile URL fragments - focus on core functionality
        assert "Install Playwright" in record.message

    def test_static_method_logging(self):
        """Test that log_availability is properly a static method"""
        # Should be callable without instance
        assert callable(BrowserChecker.log_availability)
        
        # Should work when called on class
        with patch("md_server.browser.logging") as mock_logging:
            BrowserChecker.log_availability(True)
            mock_logging.info.assert_called_once()

        with patch("md_server.browser.logging") as mock_logging:
            BrowserChecker.log_availability(False)
            mock_logging.warning.assert_called_once()

    def test_logging_exception_handling(self, caplog_with_level):
        """Test logging doesn't raise exceptions"""
        # Should not raise even with invalid input
        try:
            BrowserChecker.log_availability(None)
        except Exception as e:
            pytest.fail(f"log_availability raised an exception: {e}")
        
        # Should handle boolean-like values
        BrowserChecker.log_availability(1)  # Truthy
        BrowserChecker.log_availability(0)  # Falsy
        
        assert len(caplog_with_level.records) >= 2