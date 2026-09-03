"""Guard deprecated/removed import routes against repository regressions."""

from pathlib import Path
from uuid import uuid4


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
EXPECTED_REFERENCES = {
    "/customers" + "/upload": set(),
}
REMOVED_APPLICATION_SYMBOLS = (
    "UploadCustomer" + "ImportUseCase",
    "Upload" + "ImportCommand",
    "build_" + "import_rows",
    "def create_" + "legacy",
    ".create_" + "legacy(",
)


def _references_for(marker: str) -> set[str]:
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


def test_legacy_import_routes_have_only_explicit_references():
    actual = {marker: _references_for(marker) for marker in EXPECTED_REFERENCES}
    assert actual == EXPECTED_REFERENCES


def test_removed_legacy_upload_application_has_no_consumers():
    for symbol in REMOVED_APPLICATION_SYMBOLS:
        assert _references_for(symbol) == set()


def test_legacy_customer_upload_is_removed_from_runtime_and_openapi(client, auth_headers):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    legacy_suffix = "/customers" + "/upload"
    for prefix in ("/api/v1/" + "imports", "/api/v1/data-integration/imports"):
        path = f"{prefix}{legacy_suffix}"
        assert path not in paths
        runtime_response = client.post(path, headers=auth_headers)
        assert runtime_response.status_code == 404


def test_removed_analyze_legacy_has_no_consumers_and_returns_404(client, auth_headers):
    marker = "/analyze" + "-legacy"
    assert _references_for(marker) == set()

    suffix = f"/{uuid4()}{marker}"
    for prefix in ("/api/v1/" + "imports", "/api/v1/data-integration/imports"):
        response = client.post(f"{prefix}{suffix}", headers=auth_headers)
        assert response.status_code == 404
