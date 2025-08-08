import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    max_file_size: int = field(
        default_factory=lambda: int(
            os.getenv("MD_SERVER_MAX_FILE_SIZE", 50 * 1024 * 1024)
        )
    )
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("MD_SERVER_TIMEOUT_SECONDS", 30))
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("MD_SERVER_DEBUG", "false").lower() == "true"
    )
    allowed_file_types: List[str] = field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "text/html",
            "text/markdown",
            "application/json",
        ]
    )


def get_settings() -> Settings:
    return Settings()
