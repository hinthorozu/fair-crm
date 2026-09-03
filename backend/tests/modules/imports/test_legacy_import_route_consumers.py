"""Guard the deprecated customer-upload route against new repository consumers."""

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
ALLOWED_CONSUMERS = {
    "backend/app/modules/imports/api/routes.py",
    "backend/tests/modules/imports/test_imports_api.py",
}


def _legacy_customer_upload_references() -> set[str]:
    marker = "/customers" + "/upload"
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


def test_deprecated_customer_upload_has_only_explicit_consumers():
    assert _legacy_customer_upload_references() == ALLOWED_CONSUMERS


def test_deprecated_customer_upload_stays_marked_deprecated_in_openapi(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    legacy_suffix = "/customers" + "/upload"
    for prefix in ("/api/v1/imports", "/api/v1/data-integration/imports"):
        operation = paths[f"{prefix}{legacy_suffix}"]["post"]
        assert operation["deprecated"] is True
