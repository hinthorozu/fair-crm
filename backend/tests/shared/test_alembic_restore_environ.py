from pathlib import Path

from app.shared.database_backup.database_keys import (
    DatabaseKey,
    build_alembic_environ,
    resolve_alembic_pythonpath,
)


def test_build_alembic_environ_overrides_inherited_fair_crm_database_url(tmp_path: Path):
    backend = tmp_path / "backend"
    (backend / "app").mkdir(parents=True)
    workdir = tmp_path

    env = build_alembic_environ(
        database_key=DatabaseKey.KYROX_CORE,
        target_database_url="postgresql://postgres:postgres@127.0.0.1:5432/kyrox_core",
        alembic_workdir=workdir,
        base_environ={
            "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5432/fair_crm",
            "FAIR_CRM_DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5432/fair_crm",
            "PATH": "/usr/bin",
        },
    )

    assert env["DATABASE_URL"].endswith("/kyrox_core")
    assert env["KYROX_CORE_DATABASE_URL"].endswith("/kyrox_core")
    assert env["PYTHONPATH"] == resolve_alembic_pythonpath(workdir)
    assert env["PYTHONPATH"].endswith("backend")


def test_build_alembic_environ_sets_fair_stand_alias(tmp_path: Path):
    (tmp_path / "app").mkdir()
    env = build_alembic_environ(
        database_key=DatabaseKey.FAIR_STAND,
        target_database_url="postgresql://postgres:postgres@127.0.0.1:5432/fair_stand",
        alembic_workdir=tmp_path,
        base_environ={"DATABASE_URL": "postgresql://x/fair_crm"},
    )
    assert env["FAIR_STAND_DATABASE_URL"].endswith("/fair_stand")
    assert env["DATABASE_URL"].endswith("/fair_stand")
