from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.modules.quote_templates.infrastructure.logo_storage import resolve_logo_file
from app.modules.scraper.infrastructure.handoff_storage import is_safe_handoff_artifact_path


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows runners")
def test_managed_logo_resolver_never_follows_file_symlink(tmp_path) -> None:
    organization_id = uuid4()
    root = tmp_path / "logos"
    organization_root = root / str(organization_id)
    organization_root.mkdir(parents=True)
    target = organization_root / "target.png"
    target.write_bytes(b"target")
    link = organization_root / "owned.png"
    link.symlink_to(target)

    assert resolve_logo_file(organization_id, "owned.png", storage_root=root) is None
    assert target.read_bytes() == b"target"


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows runners")
def test_managed_logo_resolver_rejects_symlink_organization_root(tmp_path) -> None:
    organization_id = uuid4()
    root = tmp_path / "logos"
    root.mkdir()
    real_organization_root = tmp_path / "real-org"
    real_organization_root.mkdir()
    (real_organization_root / "owned.png").write_bytes(b"target")
    (root / str(organization_id)).symlink_to(real_organization_root, target_is_directory=True)

    assert resolve_logo_file(organization_id, "owned.png", storage_root=root) is None


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows runners")
def test_scraper_handoff_safety_never_follows_file_symlink(tmp_path) -> None:
    run_id = uuid4()
    root = tmp_path / "handoff"
    root.mkdir()
    target = root / f"{run_id}-target.json"
    target.write_bytes(b"target")
    link = root / f"{run_id}.json"
    link.symlink_to(target)

    assert not is_safe_handoff_artifact_path(link, run_id=run_id, base_dir=root)
    assert target.read_bytes() == b"target"


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows runners")
def test_scraper_handoff_safety_rejects_symlink_root(tmp_path) -> None:
    run_id = uuid4()
    real_root = tmp_path / "real-handoff"
    real_root.mkdir()
    path = real_root / f"{run_id}.json"
    path.write_bytes(b"target")
    root = tmp_path / "handoff"
    root.symlink_to(real_root, target_is_directory=True)

    assert not is_safe_handoff_artifact_path(path, run_id=run_id, base_dir=root)
