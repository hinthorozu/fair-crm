"""Guard deprecated/hidden import routes against new repository consumers."""

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
EXPECTED_REFERENCES = {
    "/customers" + "/upload": {
        "backend/app/modules/imports/api/routes.py",
        "backend/tests/modules/imports/test_imports_api.py",
    },
    "/analyze" + "-legacy": {
        "backend/app/modules/imports/api/routes.py",
        "backend/tests/modules/imports/test_analyze_job_parity.py",
        "backend/tests/modules/imports/test_wizard_imports_api.py",
    },
}


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


def test_legacy_import_routes_have_only_explicit_consumers():
    actual = {marker: _references_for(marker) for marker in EXPECTED_REFERENCES}
    assert actual == EXPECTED_REFERENCES


def test_deprecated_customer_upload_stays_marked_deprecated_in_openapi(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    legacy_suffix = "/customers" + "/upload"
    for prefix in ("/api/v1/" + "imports", "/api/v1/data-integration/imports"):
        operation = paths[f"{prefix}{legacy_suffix}"]["post"]
        assert operation["deprecated"] is True


def test_hidden_analyze_legacy_stays_out_of_openapi(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    hidden_suffix = "/{batch_id}/analyze" + "-legacy"
    for prefix in ("/api/v1/" + "imports", "/api/v1/data-integration/imports"):
        assert f"{prefix}{hidden_suffix}" not in paths
