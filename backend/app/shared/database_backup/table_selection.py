"""Optional table scope for custom-format backup and restore.

Full database behavior stays the default. A request enters the selected-table
path only when scope is explicitly ``selected_tables``.
"""

from __future__ import annotations

import re

from sqlalchemy import create_engine, text

SCOPE_FULL = "full"
SCOPE_SELECTED_TABLES = "selected_tables"

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TableSelectionError(ValueError):
    pass


def relation_args(tables: list[str] | None) -> list[str]:
    """Return pg_dump/pg_restore ``-t`` arguments. Empty input adds nothing."""

    if not tables:
        return []
    args: list[str] = []
    for table in tables:
        args.extend(["-t", table])
    return args


def normalize_qualified_table(value: str) -> str:
    text_value = value.strip()
    if not text_value or any(char in text_value for char in "\"'`; \t\n\r\\"):
        raise TableSelectionError(f"Invalid table name: {value}")
    if text_value.count(".") > 1:
        raise TableSelectionError(f"Invalid table name: {value}")
    if "." in text_value:
        schema, name = text_value.split(".", 1)
    else:
        schema, name = "public", text_value
    if not _IDENT.fullmatch(schema) or not _IDENT.fullmatch(name):
        raise TableSelectionError(f"Invalid table name: {value}")
    return f"{schema}.{name}"


def normalize_table_list(tables: list[str] | None) -> list[str]:
    if not tables:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in tables:
        qualified = normalize_qualified_table(item)
        if qualified in seen:
            raise TableSelectionError(f"Duplicate table: {qualified}")
        seen.add(qualified)
        normalized.append(qualified)
    return normalized


def resolve_scope(
    *,
    scope: str | None,
    tables: list[str] | None,
) -> tuple[str, list[str] | None]:
    """Return ``(scope, tables)``.

    ``None``, ``full``, and an empty table list stay on the full path.
    Selected mode is active only for an explicit ``selected_tables`` scope.
    """

    selected_scope = scope or SCOPE_FULL
    if selected_scope == SCOPE_FULL:
        return SCOPE_FULL, None
    if selected_scope != SCOPE_SELECTED_TABLES:
        raise TableSelectionError("Invalid backup scope")
    selected = normalize_table_list(tables)
    if not selected:
        raise TableSelectionError("At least one table is required")
    return SCOPE_SELECTED_TABLES, selected


def scope_manifest(*, scope: str, tables: list[str] | None = None) -> dict[str, object]:
    if scope == SCOPE_SELECTED_TABLES:
        return {"scope": SCOPE_SELECTED_TABLES, "tables": list(tables or [])}
    return {"scope": SCOPE_FULL}


def selected_tables_from_manifest(manifest: dict | None) -> list[str] | None:
    """Return selected tables, or None when the artifact/job is a full operation."""

    if not isinstance(manifest, dict):
        return None
    if manifest.get("scope") != SCOPE_SELECTED_TABLES:
        return None
    raw = manifest.get("tables")
    if not isinstance(raw, list):
        raise TableSelectionError("Selected restore is missing tables")
    selected = normalize_table_list([str(item) for item in raw])
    if not selected:
        raise TableSelectionError("At least one table is required")
    return selected


_TOC_DESCRIPTIONS = (
    "FK CONSTRAINT",
    "TABLE DATA",
    "SEQUENCE OWNED BY",
    "SEQUENCE SET",
    "ROW SECURITY",
    "DEFAULT ACL",
    "MATERIALIZED VIEW",
    "FOREIGN TABLE",
    "CONSTRAINT",
    "SEQUENCE",
    "INDEX",
    "TRIGGER",
    "COMMENT",
    "POLICY",
    "TABLE",
    "VIEW",
    "RULE",
    "ACL",
    "DATABASE",
    "ENCODING",
    "STDSTRINGS",
    "SEARCHPATH",
)


def restore_list_for_tables(toc: str, tables: list[str]) -> str:
    """Build a ``pg_restore -L`` list for the selected tables.

    PostgreSQL 18 ``pg_restore -t`` does not accept ``schema.table`` and does
    not restore indexes, constraints, or sequences. The verbose TOC already
    records those archive entries as dependents of the table. This keeps those
    entries and does not add any other table.
    """

    entries: list[dict[str, object]] = []
    for raw_line in toc.splitlines():
        if raw_line.startswith(";") and "depends on:" in raw_line:
            if entries:
                depends = entries[-1]["depends"]
                assert isinstance(depends, list)
                depends.extend(int(item) for item in raw_line.split(":", 1)[1].split())
            continue
        matched = re.match(r"^(\d+); \d+ \d+ (.+)$", raw_line)
        if not matched:
            continue
        dump_id = int(matched.group(1))
        remainder = matched.group(2)
        description = next((item for item in _TOC_DESCRIPTIONS if remainder.startswith(item + " ")), "")
        schema = ""
        name = ""
        if description:
            tail = remainder[len(description) + 1 :].split()
            if len(tail) >= 2:
                schema = tail[0]
                name = tail[1] if len(tail) == 2 else " ".join(tail[1:-1])
        entries.append(
            {
                "dump_id": dump_id,
                "description": description,
                "schema": schema,
                "name": name,
                "depends": [],
            }
        )

    wanted = set(tables)
    included = {
        int(entry["dump_id"])
        for entry in entries
        if entry["description"] == "TABLE" and f"{entry['schema']}.{entry['name']}" in wanted
    }
    found = {
        f"{entry['schema']}.{entry['name']}"
        for entry in entries
        if int(entry["dump_id"]) in included
    }
    missing = [table for table in tables if table not in found]
    if missing:
        raise TableSelectionError(f"Table is not in the backup archive: {', '.join(missing)}")

    changed = True
    while changed:
        changed = False
        for entry in entries:
            dump_id = int(entry["dump_id"])
            if dump_id in included or entry["description"] == "TABLE":
                continue
            depends = entry["depends"]
            assert isinstance(depends, list)
            if any(dependency in included for dependency in depends):
                included.add(dump_id)
                changed = True

    rendered: list[str] = []
    for raw_line in toc.splitlines():
        matched = re.match(r"^(\d+);", raw_line)
        if matched and int(matched.group(1)) not in included:
            rendered.append(";" + raw_line)
            continue
        rendered.append(raw_line)
    return "\n".join(rendered) + "\n"


def parse_restore_toc_tables(toc: str) -> list[str]:
    """Read relation names from ``pg_restore -l`` output.

    ``TABLE DATA`` lines are not table definitions. Sequences, indexes and
    constraints stay in the archive and are not added here.
    """

    tables: list[str] = []
    seen: set[str] = set()
    for raw_line in toc.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if len(parts) < 6 or parts[3] != "TABLE":
            continue
        schema, name = parts[4], parts[5]
        if schema == "DATA":
            continue
        if not _IDENT.fullmatch(schema) or not _IDENT.fullmatch(name):
            continue
        qualified = f"{schema}.{name}"
        if qualified in seen:
            continue
        seen.add(qualified)
        tables.append(qualified)
    return tables


def list_public_base_tables(database_url: str) -> list[str]:
    """List ``public`` base tables from ``information_schema``.

    This is the same catalog filter the post-restore health check uses for
    table existence. System catalogs are not in ``public``.
    """

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
            )
            return [f"public.{row[0]}" for row in rows]
    finally:
        engine.dispose()


def require_tables_in_catalog(tables: list[str], catalog: list[str]) -> None:
    known = set(catalog)
    missing = [table for table in tables if table not in known]
    if missing:
        raise TableSelectionError(f"Unknown table: {', '.join(missing)}")


def require_tables_in_archive(tables: list[str], archive_tables: list[str]) -> None:
    known = set(archive_tables)
    missing = [table for table in tables if table not in known]
    if missing:
        raise TableSelectionError(f"Table is not in the backup archive: {', '.join(missing)}")
