"""
Configuration management for the SDK.
"""

import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class SDKConfig:
    """Configuration for SDK operations."""
    
    debug: bool = False
    log_level: str = "INFO"
    default_timeout: int = 30
    default_max_file_size_mb: int = 50
    
    def setup_logging(self) -> None:
        """Configure logging for the SDK."""
        level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        logger = logging.getLogger("md_server.sdk")
        logger.setLevel(level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(f"md_server.sdk.{name}")