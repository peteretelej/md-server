import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"