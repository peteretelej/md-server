import os
from dataclasses import dataclass


@dataclass
class Settings:
    max_file_size: int = int(os.getenv("MD_SERVER_MAX_FILE_SIZE", 50 * 1024 * 1024))
    timeout_seconds: int = int(os.getenv("MD_SERVER_TIMEOUT_SECONDS", 30))
    debug: bool = os.getenv("MD_SERVER_DEBUG", "false").lower() == "true"


def get_settings() -> Settings:
    return Settings()
