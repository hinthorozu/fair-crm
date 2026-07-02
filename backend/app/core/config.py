from functools import lru_cache
from uuid import UUID

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    from app.integrations.kyrox_core.dev_bypass import validate_dev_bypass_settings

    validate_dev_bypass_settings(settings)
    return settings
