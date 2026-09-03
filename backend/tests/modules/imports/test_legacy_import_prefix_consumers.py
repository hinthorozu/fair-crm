"""Prevent repository consumers from depending on the duplicate legacy import mount."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SEARCH_ROOTS = ("backend", "frontend", "scripts", ".github", ".kyrox")
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".yml",
    ".yaml",
    ".sh",
}


def _legacy_prefix_references() -> set[str]:
    marker = "/api/v1/" + "imports"
    references: set[str] = set()

    for root_name in SEARCH_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if marker in content:
                references.add(path.relative_to(REPO_ROOT).as_posix())

    return references


def test_duplicate_import_prefix_has_no_repository_consumers():
    assert _legacy_prefix_references() == set()


def test_legacy_import_mount_is_hidden_from_openapi_but_still_callable(client, auth_headers):
    legacy_prefix = "/api/v1/" + "imports"
    canonical_prefix = "/api/v1/data-integration/imports"

    response = client.get("/openapi.json")
    assert response.status_code == 200
    documented_paths = response.json()["paths"]
    assert any(path.startswith(canonical_prefix) for path in documented_paths)
    assert not any(path.startswith(legacy_prefix) for path in documented_paths)

    # The compatibility mount still resolves at runtime. Missing required multipart
    # fields are validated as 422; a removed route would return 404 instead.
    legacy_upload = client.post(f"{legacy_prefix}/upload", headers=auth_headers)
    assert legacy_upload.status_code == 422
