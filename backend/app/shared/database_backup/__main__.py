"""CLI entry point used by dev PowerShell scripts and operators."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import get_settings
from app.shared.database_backup.engine import pg_dump_custom, pg_restore_custom, verify_backup_dump
from app.shared.database_backup.paths import generate_backup_filename, get_backups_dir, resolve_backup_path


def _cmd_backup(args: argparse.Namespace) -> int:
    settings = get_settings()
    output = Path(args.output) if args.output else get_backups_dir() / generate_backup_filename()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = pg_dump_custom(database_url=settings.database_url, output_path=output)
    print(f"Backup complete: {result.path}")
    print(f"Size: {result.size_bytes} bytes")
    print(f"Checksum: {result.checksum_sha256}")
    print(f"TOC items: {result.toc_entry_count}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    settings = get_settings()
    path = resolve_backup_path(Path(args.file).name)
    verified = verify_backup_dump(database_url=settings.database_url, dump_path=path)
    print(f"Valid backup: {verified.path}")
    print(f"Size: {verified.size_bytes} bytes")
    print(f"TOC items: {verified.toc_entry_count}")
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    settings = get_settings()
    path = resolve_backup_path(Path(args.file).name)
    conn_db = settings.database_url.rsplit("/", 1)[-1].split("?")[0]
    if args.dry_run:
        verify_backup_dump(database_url=settings.database_url, dump_path=path)
        print("Dry-run OK - no database changes made.")
        return 0
    if args.confirm != conn_db:
        print(f"Restore cancelled. Expected confirmation '{conn_db}'.", file=sys.stderr)
        return 1
    pg_restore_custom(database_url=settings.database_url, dump_path=path)
    print("Restore complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fair CRM database backup engine")
    sub = parser.add_subparsers(dest="command", required=True)

    backup = sub.add_parser("backup", help="Create a custom-format PostgreSQL backup")
    backup.add_argument("--output", help="Output .dump path")
    backup.set_defaults(func=_cmd_backup)

    verify = sub.add_parser("verify", help="Verify a backup file")
    verify.add_argument("file", help="Backup file name or path")
    verify.set_defaults(func=_cmd_verify)

    restore = sub.add_parser("restore", help="Restore a backup file")
    restore.add_argument("file", help="Backup file name or path")
    restore.add_argument("--confirm", help="Target database name confirmation")
    restore.add_argument("--dry-run", action="store_true")
    restore.set_defaults(func=_cmd_restore)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
