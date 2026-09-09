from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable
from uuid import UUID
from zipfile import BadZipFile, ZIP_STORED, ZipFile, ZipInfo

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CLOSURE_PACKAGE_ROOT = _BACKEND_ROOT / "data" / "closure-packages"
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class ClosurePackageStorageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PackageMember:
    path: str
    content: bytes


@dataclass(frozen=True, slots=True)
class StoredPackage:
    path: Path
    relative_locator: str
    digest: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class InspectedPackage:
    manifest: dict
    manifest_digest: str
    package_digest: str
    byte_size: int


def file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_manifest_bytes(manifest: dict) -> bytes:
    return (
        json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )


def _safe_member_path(value: str) -> bool:
    candidate = Path(value)
    return (
        value == candidate.as_posix()
        and not candidate.is_absolute()
        and ".." not in candidate.parts
        and value not in {"", "."}
    )


def resolve_package_path(
    organization_id: UUID,
    execution_id: UUID,
    package_id: UUID,
    *,
    storage_root: Path | None = None,
) -> tuple[Path, str]:
    root = (storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT).resolve()
    relative = Path(str(organization_id)) / str(execution_id) / f"{package_id}.zip"
    organization_root = root / str(organization_id)
    execution_root = organization_root / str(execution_id)

    if organization_root.exists() and organization_root.is_symlink():
        raise ClosurePackageStorageError("Closure package organization root cannot be a symlink")
    if execution_root.exists() and execution_root.is_symlink():
        raise ClosurePackageStorageError("Closure package execution root cannot be a symlink")

    execution_root.mkdir(parents=True, exist_ok=True)
    resolved_execution = execution_root.resolve()
    if not resolved_execution.is_relative_to(root):
        raise ClosurePackageStorageError("Closure package path escapes configured storage root")

    unresolved_candidate = resolved_execution / f"{package_id}.zip"
    if unresolved_candidate.exists() and unresolved_candidate.is_symlink():
        raise ClosurePackageStorageError("Canonical closure package target cannot be a symlink")
    candidate = unresolved_candidate.resolve()
    if not candidate.is_relative_to(resolved_execution):
        raise ClosurePackageStorageError("Closure package path escapes execution root")
    return candidate, relative.as_posix()


def _write_member(archive: ZipFile, member: PackageMember) -> None:
    if not _safe_member_path(member.path):
        raise ClosurePackageStorageError("Unsafe closure package member path")
    info = ZipInfo(member.path, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o600 << 16
    archive.writestr(info, member.content)


def write_immutable_package(
    *,
    organization_id: UUID,
    execution_id: UUID,
    package_id: UUID,
    manifest: dict,
    members: Iterable[PackageMember],
    storage_root: Path | None = None,
) -> StoredPackage:
    target, locator = resolve_package_path(
        organization_id,
        execution_id,
        package_id,
        storage_root=storage_root,
    )
    member_list = sorted(members, key=lambda item: item.path)
    paths = [member.path for member in member_list]
    if len(paths) != len(set(paths)):
        raise ClosurePackageStorageError("Duplicate closure package member path")

    manifest_bytes = canonical_manifest_bytes(manifest)

    with NamedTemporaryFile(
        dir=target.parent,
        prefix=f".{package_id}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary_path = Path(handle.name)

    try:
        with ZipFile(temporary_path, "w", compression=ZIP_STORED, allowZip64=True) as archive:
            _write_member(archive, PackageMember("manifest.json", manifest_bytes))
            for member in member_list:
                _write_member(archive, member)
        with temporary_path.open("rb") as handle:
            os.fsync(handle.fileno())
        generated_digest = file_digest(temporary_path)
        generated_size = temporary_path.stat().st_size

        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ClosurePackageStorageError("Canonical closure package target is unsafe")
            current_digest = file_digest(target)
            current_size = target.stat().st_size
            if current_digest != generated_digest or current_size != generated_size:
                raise ClosurePackageStorageError(
                    "Existing canonical closure package bytes do not match deterministic regeneration"
                )
            return StoredPackage(
                path=target,
                relative_locator=locator,
                digest=current_digest,
                byte_size=current_size,
            )

        os.replace(temporary_path, target)
        return StoredPackage(
            path=target,
            relative_locator=locator,
            digest=generated_digest,
            byte_size=generated_size,
        )
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def resolve_stored_locator(locator: str, *, storage_root: Path | None = None) -> Path:
    candidate = Path(locator)
    if candidate.is_absolute() or ".." in candidate.parts or locator != candidate.as_posix():
        raise ClosurePackageStorageError("Unsafe closure package storage locator")
    root = (storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT).resolve()
    unresolved = root / candidate
    if unresolved.exists() and unresolved.is_symlink():
        raise ClosurePackageStorageError("Closure package locator cannot be a symlink")
    resolved = unresolved.resolve()
    if not resolved.is_relative_to(root):
        raise ClosurePackageStorageError("Closure package locator escapes configured storage root")
    return resolved


def inspect_package(path: Path) -> InspectedPackage:
    if not path.is_file() or path.is_symlink():
        raise ClosurePackageStorageError("Canonical closure package bytes are unavailable")

    try:
        package_digest = file_digest(path)
        byte_size = path.stat().st_size
        with ZipFile(path, "r") as archive:
            names = archive.namelist()
            if names.count("manifest.json") != 1:
                raise ClosurePackageStorageError("Closure package manifest membership is invalid")
            manifest_bytes = archive.read("manifest.json")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            canonical = canonical_manifest_bytes(manifest)
            if canonical != manifest_bytes:
                raise ClosurePackageStorageError("Closure package manifest encoding is not canonical")
            manifest_digest = sha256(canonical).hexdigest()

            expected_members = manifest.get("members")
            if not isinstance(expected_members, list):
                raise ClosurePackageStorageError("Closure package manifest member registry is missing")
            expected_names = {"manifest.json"}
            for member in expected_members:
                if not isinstance(member, dict):
                    raise ClosurePackageStorageError("Closure package member registry is malformed")
                member_path = member.get("path")
                digest = member.get("sha256")
                member_size = member.get("byte_size")
                if not isinstance(member_path, str) or not _safe_member_path(member_path):
                    raise ClosurePackageStorageError("Closure package member path is invalid")
                if member_path in expected_names:
                    raise ClosurePackageStorageError("Closure package member registry contains duplicates")
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ClosurePackageStorageError("Closure package member digest is invalid")
                if not isinstance(member_size, int) or member_size < 0:
                    raise ClosurePackageStorageError("Closure package member size is invalid")
                payload = archive.read(member_path)
                if sha256(payload).hexdigest() != digest or len(payload) != member_size:
                    raise ClosurePackageStorageError("Closure package member integrity verification failed")
                expected_names.add(member_path)
            if set(names) != expected_names:
                raise ClosurePackageStorageError("Closure package archive membership verification failed")
            return InspectedPackage(
                manifest=manifest,
                manifest_digest=manifest_digest,
                package_digest=package_digest,
                byte_size=byte_size,
            )
    except ClosurePackageStorageError:
        raise
    except (BadZipFile, OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise ClosurePackageStorageError("Closure package integrity verification failed") from exc


def verify_package(
    *,
    path: Path,
    expected_package_digest: str,
    expected_manifest_digest: str,
) -> dict:
    inspected = inspect_package(path)
    if inspected.package_digest != expected_package_digest:
        raise ClosurePackageStorageError("Closure package byte digest verification failed")
    if inspected.manifest_digest != expected_manifest_digest:
        raise ClosurePackageStorageError("Closure package manifest digest verification failed")
    return inspected.manifest
