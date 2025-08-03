import pytest
import os
from unittest.mock import patch
from md_server.core.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()
        
        assert settings.max_file_size == 50 * 1024 * 1024
        assert settings.timeout_seconds == 30
        assert "application/pdf" in settings.allowed_file_types
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in settings.allowed_file_types

    def test_environment_variable_override(self):
        with patch.dict(os.environ, {
            'MD_SERVER_MAX_FILE_SIZE': '100000000',
            'MD_SERVER_TIMEOUT_SECONDS': '60'
        }):
            settings = Settings()
            assert settings.max_file_size == 100000000
            assert settings.timeout_seconds == 60

    def test_allowed_file_types_default(self):
        settings = Settings()
        expected_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "text/html",
            "text/markdown",
        ]
        assert settings.allowed_file_types == expected_types

    def test_settings_validation(self):
        settings = Settings(
            max_file_size=1024,
            timeout_seconds=5,
            allowed_file_types=["text/plain"]
        )
        assert settings.max_file_size == 1024
        assert settings.timeout_seconds == 5
        assert settings.allowed_file_types == ["text/plain"]


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_with_env_vars(self):
        with patch.dict(os.environ, {
            'MD_SERVER_MAX_FILE_SIZE': '20971520',
            'MD_SERVER_TIMEOUT_SECONDS': '45'
        }):
            settings = get_settings()
            assert settings.max_file_size == 20971520
            assert settings.timeout_seconds == 45