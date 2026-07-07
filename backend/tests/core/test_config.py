import pytest

from app.core.config import Settings, get_settings


def test_database_url_prefers_fair_crm_env_file_when_shell_points_at_core(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg2://postgres:secret@localhost:5432/fair_crm\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:secret@localhost:5432/kyrox_core",
    )

    settings = Settings(_env_file=env_file)

    assert "fair_crm" in settings.database_url
    assert "kyrox_core" not in settings.database_url


def test_get_settings_uses_backend_env_file_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert "fair_crm" in settings.database_url.lower()
