from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GuardianMapStudioSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STUDIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///guardianmapstudio.db"

    # Export
    export_dir: str = "exports"
    export_indent: int = 2

    # Geometry
    snap_tolerance_m: float = 0.5
    coordinate_precision: int = 7

    # OSM Import
    osm_max_file_size_mb: int = 10
    osm_max_ways: int = 500

    # Logging
    log_level: str = "INFO"
    log_file: str = "guardianmapstudio.log"
    log_rotation_mb: int = 50
    log_retention_days: int = 30
