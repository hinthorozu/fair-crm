from pathlib import Path

from app.shared.database_backup import engine
from app.shared.database_backup.table_selection import (
    SCOPE_FULL,
    SCOPE_SELECTED_TABLES,
    TableSelectionError,
    normalize_table_list,
    parse_restore_toc_tables,
    relation_args,
    resolve_scope,
    restore_list_for_tables,
    selected_tables_from_manifest,
)


TOC = """
;
; Archive created at 2026-10-01 03:15:21 UTC
;
242; 1259 49908 TABLE public crm_quotes postgres
3637; 0 49908 TABLE DATA public crm_quotes postgres
3479; 2606 68628 CONSTRAINT public crm_quotes crm_quotes_pkey postgres
3480; 1259 68767 INDEX public ix_crm_quotes_customer_id postgres
3486; 2606 68967 FK CONSTRAINT public crm_quotes crm_quotes_customer_id_fkey postgres
223; 1259 107473 SEQUENCE public fair_stand_categories_id_seq postgres
3553; 0 0 SEQUENCE SET public fair_stand_categories_id_seq postgres
"""


def test_resolve_scope_defaults_to_full():
    assert resolve_scope(scope=None, tables=None) == (SCOPE_FULL, None)
    assert resolve_scope(scope=None, tables=[]) == (SCOPE_FULL, None)
    assert resolve_scope(scope=SCOPE_FULL, tables=["public.crm_quotes"]) == (SCOPE_FULL, None)
    assert resolve_scope(scope=SCOPE_FULL, tables=[]) == (SCOPE_FULL, None)


def test_resolve_scope_requires_tables_only_when_selected():
    scope, tables = resolve_scope(scope=SCOPE_SELECTED_TABLES, tables=["crm_quotes", "public.crm_contacts"])
    assert scope == SCOPE_SELECTED_TABLES
    assert tables == ["public.crm_quotes", "public.crm_contacts"]
    try:
        resolve_scope(scope=SCOPE_SELECTED_TABLES, tables=[])
    except TableSelectionError as exc:
        assert "At least one table" in str(exc)
    else:
        raise AssertionError("empty selected scope must be rejected")


def test_normalize_rejects_duplicates_and_injection():
    try:
        normalize_table_list(["public.crm_quotes", "crm_quotes"])
    except TableSelectionError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("duplicate tables must be rejected")
    for unsafe in ("public.crm_quotes;drop", "public.crm quotes", 'public."crm"', "public.crm_quotes\\n"):
        try:
            normalize_table_list([unsafe])
        except TableSelectionError:
            continue
        raise AssertionError(f"unsafe name was accepted: {unsafe}")


def test_parse_toc_returns_table_definitions_only():
    assert parse_restore_toc_tables(TOC) == ["public.crm_quotes"]


VERBOSE_TOC = """
;
; Archive created at 2026-10-01 03:51:31 UTC
;
222; 1259 221756 TABLE public child_probe postgres
221; 1259 221755 SEQUENCE public child_probe_id_seq postgres
;	depends on: 222
220; 1259 221745 TABLE public parent_probe postgres
219; 1259 221744 SEQUENCE public parent_probe_id_seq postgres
;	depends on: 220
3486; 0 221756 TABLE DATA public child_probe postgres
;	depends on: 222
3484; 0 221745 TABLE DATA public parent_probe postgres
;	depends on: 220
3493; 0 0 SEQUENCE SET public child_probe_id_seq postgres
;	depends on: 221
3494; 0 0 SEQUENCE SET public parent_probe_id_seq postgres
;	depends on: 219
3333; 2606 221764 CONSTRAINT public child_probe child_probe_pkey postgres
;	depends on: 222
3329; 2606 221754 CONSTRAINT public parent_probe parent_probe_name_key postgres
;	depends on: 220
3331; 2606 221752 CONSTRAINT public parent_probe parent_probe_pkey postgres
;	depends on: 220
3334; 1259 221770 INDEX public ix_child_probe_note postgres
;	depends on: 222
3335; 2606 221765 FK CONSTRAINT public child_probe child_probe_parent_id_fkey postgres
;	depends on: 222 3331 220
"""


def test_restore_list_keeps_table_objects_without_adding_other_tables():
    listing = restore_list_for_tables(VERBOSE_TOC, ["public.child_probe"])
    active = [line for line in listing.splitlines() if line[:1].isdigit()]
    joined = "\n".join(active)
    assert "TABLE public child_probe " in joined
    assert "SEQUENCE public child_probe_id_seq " in joined
    assert "SEQUENCE SET public child_probe_id_seq " in joined
    assert "CONSTRAINT public child_probe child_probe_pkey " in joined
    assert "INDEX public ix_child_probe_note " in joined
    assert "FK CONSTRAINT public child_probe " in joined
    assert "parent_probe" not in joined


def test_full_manifest_does_not_select_tables():
    assert selected_tables_from_manifest(None) is None
    assert selected_tables_from_manifest({"scope": "full"}) is None
    assert selected_tables_from_manifest({"scope": "full", "tables": ["public.crm_quotes"]}) is None


def test_relation_args_are_absent_for_full_scope():
    assert relation_args(None) == []
    assert relation_args([]) == []
    assert relation_args(["public.crm_quotes", "public.crm_contacts"]) == [
        "-t",
        "public.crm_quotes",
        "-t",
        "public.crm_contacts",
    ]


def _capture_dump(monkeypatch, tables):
    commands: list[list[str]] = []
    monkeypatch.setattr(engine, "_get_backup_toolchain", lambda conn: ("local", None))
    monkeypatch.setattr(engine, "_resolve_pg_tool", lambda name: "pg_dump")
    monkeypatch.setattr(engine, "verify_backup_dump", lambda **kwargs: type("V", (), {"size_bytes": 4, "toc_entry_count": 1})())
    monkeypatch.setattr(engine, "sha256_file", lambda path: "a" * 64)

    def _run(args, **kwargs):
        commands.append(args)
        Path(args[args.index("-f") + 1]).write_bytes(b"PGDMP")

    monkeypatch.setattr(engine, "_run_command", _run)
    kwargs = {"database_url": "postgresql://postgres:postgres@localhost:5432/fair_crm", "output_path": Path("ignored.dump")}
    if tables is not None:
        kwargs["tables"] = tables
    engine.pg_dump_custom(**kwargs)
    return commands[0]


def test_full_pg_dump_has_no_table_switch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command = _capture_dump(monkeypatch, None)
    assert command[1] == "-Fc"
    assert "--no-owner" in command
    assert "--no-acl" in command
    assert "-t" not in command
    empty = _capture_dump(monkeypatch, [])
    assert "-t" not in empty


def test_selected_pg_dump_appends_native_table_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command = _capture_dump(monkeypatch, ["public.crm_customers", "public.crm_contacts", "public.crm_quotes"])
    assert command[1] == "-Fc"
    assert command[command.index("--no-acl") + 1 :] == [
        "-t",
        "public.crm_customers",
        "-t",
        "public.crm_contacts",
        "-t",
        "public.crm_quotes",
    ]


def _capture_restore(monkeypatch, tables):
    commands: list[list[str]] = []
    lists: list[str] = []
    monkeypatch.setattr(engine, "_get_toolchain", lambda conn: ("local", None))
    monkeypatch.setattr(engine, "_resolve_pg_tool", lambda name: "pg_restore")
    monkeypatch.setattr(engine, "read_custom_dump_toc", lambda **kwargs: VERBOSE_TOC)

    def _run(args, **kwargs):
        commands.append(args)
        if "-L" in args:
            lists.append(Path(args[args.index("-L") + 1]).read_text(encoding="utf-8"))
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(engine.subprocess, "run", _run)
    kwargs = {
        "database_url": "postgresql://postgres:postgres@localhost:5432/fair_crm",
        "dump_path": Path("restore.dump"),
    }
    Path("restore.dump").write_bytes(b"PGDMP")
    if tables is not None:
        kwargs["tables"] = tables
    engine.pg_restore_custom(**kwargs)
    return commands[0], lists


def test_full_pg_restore_keeps_clean_flags_without_table_switch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command, lists = _capture_restore(monkeypatch, None)
    for flag in ("--clean", "--if-exists", "--single-transaction", "--no-owner", "--no-acl", "--exit-on-error"):
        assert flag in command
    assert "-t" not in command
    assert "-L" not in command
    assert lists == []
    empty_command, empty_lists = _capture_restore(monkeypatch, [])
    assert "-t" not in empty_command
    assert "-L" not in empty_command
    assert empty_lists == []


def test_selected_pg_restore_uses_archive_list_without_table_switch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command, lists = _capture_restore(monkeypatch, ["public.child_probe"])
    for flag in ("--clean", "--if-exists", "--single-transaction", "--no-owner", "--no-acl", "--exit-on-error"):
        assert flag in command
    assert "-t" not in command
    assert command[command.index("--exit-on-error") + 1] == "-L"
    assert command[-1] == "restore.dump"
    assert "INDEX public ix_child_probe_note " in lists[0]
    assert "TABLE public parent_probe " not in "\n".join(
        line for line in lists[0].splitlines() if line[:1].isdigit()
    )
