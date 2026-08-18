from pathlib import Path

from app.shared.database_backup import engine


def _dump_file(tmp_path: Path) -> Path:
    path = tmp_path / "restore.dump"
    path.write_bytes(b"PGDMP-test")
    return path


def test_pg_restore_local_is_atomic(tmp_path, monkeypatch):
    commands: list[list[str]] = []
    monkeypatch.setattr(engine, "_get_toolchain", lambda conn: ("local", None))
    monkeypatch.setattr(engine, "_resolve_pg_tool", lambda name: "pg_restore")

    def _run(args, **kwargs):
        commands.append(args)
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(engine.subprocess, "run", _run)

    engine.pg_restore_custom(
        database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
        dump_path=_dump_file(tmp_path),
    )

    assert len(commands) == 1
    assert "--clean" in commands[0]
    assert "--single-transaction" in commands[0]
    assert "--exit-on-error" in commands[0]


def test_pg_restore_docker_is_atomic(tmp_path, monkeypatch):
    commands: list[list[str]] = []
    exec_calls: list[list[str]] = []
    monkeypatch.setattr(engine, "_get_toolchain", lambda conn: ("docker", "kyrox-postgres-dev"))
    monkeypatch.setattr(engine, "_docker_cp_to", lambda container, local_path, remote_path: None)
    monkeypatch.setattr(engine, "_docker_exec", lambda container, args: exec_calls.append(args))

    def _run(args, **kwargs):
        commands.append(args)
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(engine.subprocess, "run", _run)

    engine.pg_restore_custom(
        database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
        dump_path=_dump_file(tmp_path),
    )

    assert len(commands) == 1
    restore_command = commands[0]
    assert restore_command[:3] == ["docker", "exec", "kyrox-postgres-dev"]
    assert "--clean" in restore_command
    assert "--single-transaction" in restore_command
    assert "--exit-on-error" in restore_command
    assert exec_calls[-1][:2] == ["rm", "-f"]
