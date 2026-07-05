from functools import lru_cache
from uuid import UUID

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm"
    jwt_secret_key: str = "change-me-in-production-use-a-long-random-string"
    smtp_secret_encryption_key: str | None = Field(
        default=None,
        validation_alias="FAIR_CRM_SMTP_SECRET_ENCRYPTION_KEY",
    )
    jwt_algorithm: str = "HS256"
    kyrox_core_base_url: str = "http://localhost:8000"
    app_env: str = "development"
    log_level: str = "INFO"
    app_version: str = "1.0.0-phase2"
    dev_bypass_core: bool = Field(default=False, validation_alias="FAIR_CRM_DEV_BYPASS_CORE")
    dev_bypass_token: str = Field(default="dev-bypass", validation_alias="FAIR_CRM_DEV_BYPASS_TOKEN")
    dev_user_id: UUID | None = Field(default=None, validation_alias="FAIR_CRM_DEV_USER_ID")
    dev_user_email: str = Field(default="dev@example.com", validation_alias="FAIR_CRM_DEV_USER_EMAIL")
    dev_organization_id: UUID | None = Field(default=None, validation_alias="FAIR_CRM_DEV_ORGANIZATION_ID")
    postgres_docker_container: str = Field(
        default="kyrox-postgres-dev",
        validation_alias="FAIR_CRM_POSTGRES_DOCKER_CONTAINER",
    )
    database_restore_enabled: bool = Field(
        default=False,
        validation_alias="FAIR_CRM_DATABASE_RESTORE_ENABLED",
    )
    import_max_file_size_mb: int = Field(
        default=50,
        validation_alias=AliasChoices("IMPORT_MAX_FILE_SIZE_MB", "FAIR_CRM_IMPORT_MAX_FILE_SIZE_MB"),
    )
    import_max_rows: int = Field(
        default=50_000,
        validation_alias=AliasChoices("IMPORT_MAX_ROWS", "FAIR_CRM_IMPORT_MAX_ROWS"),
    )
    import_max_columns: int = Field(
        default=100,
        validation_alias=AliasChoices("IMPORT_MAX_COLUMNS", "FAIR_CRM_IMPORT_MAX_COLUMNS"),
    )
    import_max_sheets: int = Field(
        default=20,
        validation_alias=AliasChoices("IMPORT_MAX_SHEETS", "FAIR_CRM_IMPORT_MAX_SHEETS"),
    )
    import_mapping_sample_rows: int = Field(
        default=10,
        validation_alias=AliasChoices("IMPORT_MAPPING_SAMPLE_ROWS", "FAIR_CRM_IMPORT_MAPPING_SAMPLE_ROWS"),
    )
    import_grid_preview_rows: int = Field(
        default=50,
        validation_alias=AliasChoices("IMPORT_GRID_PREVIEW_ROWS", "FAIR_CRM_IMPORT_GRID_PREVIEW_ROWS"),
    )
    import_analyze_chunk_size: int = Field(
        default=500,
        validation_alias=AliasChoices("IMPORT_ANALYZE_CHUNK_SIZE", "FAIR_CRM_IMPORT_ANALYZE_CHUNK_SIZE"),
    )
    db_pool_size: int = Field(default=10, validation_alias="FAIR_CRM_DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="FAIR_CRM_DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, validation_alias="FAIR_CRM_DB_POOL_TIMEOUT")
    performance_slow_request_ms: int = Field(
        default=500,
        validation_alias="FAIR_CRM_SLOW_REQUEST_MS",
    )
    performance_slow_query_ms: int = Field(
        default=100,
        validation_alias="FAIR_CRM_SLOW_QUERY_MS",
    )
    scraper_browser_headless: bool = Field(
        default=True,
        validation_alias=AliasChoices("SCRAPER_BROWSER_HEADLESS", "FAIR_CRM_SCRAPER_BROWSER_HEADLESS"),
    )
    scraper_browser_timeout_ms: int = Field(
        default=30_000,
        validation_alias=AliasChoices("SCRAPER_BROWSER_TIMEOUT_MS", "FAIR_CRM_SCRAPER_BROWSER_TIMEOUT_MS"),
    )
    scraper_browser_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        validation_alias=AliasChoices("SCRAPER_BROWSER_USER_AGENT", "FAIR_CRM_SCRAPER_BROWSER_USER_AGENT"),
    )
    scraper_browser_channel: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SCRAPER_BROWSER_CHANNEL", "FAIR_CRM_SCRAPER_BROWSER_CHANNEL"),
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    from app.integrations.kyrox_core.dev_bypass import validate_dev_bypass_settings

    validate_dev_bypass_settings(settings)
    return settings
