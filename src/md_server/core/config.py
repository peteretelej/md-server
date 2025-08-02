from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/html",
        "text/markdown",
    ]
    timeout_seconds: int = 30
    
    class Config:
        env_prefix = "MD_SERVER_"

def get_settings() -> Settings:
    return Settings()