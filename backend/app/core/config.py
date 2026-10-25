from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    max_upload_mb: int = Field(default=20, ge=1, le=500)
    max_image_pixels: int = Field(default=40_000_000, ge=1)
    max_image_dimension: int = Field(default=10_000, ge=1)
    max_working_dimension: int = Field(default=2048, ge=256)
    change_threshold: int = Field(default=38, ge=1, le=255)
    min_region_area: int = Field(default=24, ge=1)
    min_region_percent: float = Field(default=0.0001, ge=0, le=1)
    report_retention_hours: int = Field(default=24, ge=1)
    storage_dir: Path = Path("backend/data")
    samples_dir: Path = Path("data/samples")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    vision_provider: str = "disabled"
    vision_api_key: str | None = None
    vision_model: str | None = None
    vision_request_timeout_seconds: float = Field(default=25, ge=1, le=120)
    vision_max_image_dimension: int = Field(default=1600, ge=256, le=4096)
    vision_max_image_bytes: int = Field(default=5_000_000, ge=100_000)
    vision_max_payload_bytes: int = Field(default=12_000_000, ge=500_000)
    vision_max_region_crops: int = Field(default=3, ge=0, le=6)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
