from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = BACKEND_ROOT / "app/modules/quote_templates/api/dependencies.py"
ROUTES = BACKEND_ROOT / "app/modules/quote_templates/api/routes.py"


def test_logo_upload_accepts_create_or_update_permission():
    dependency_source = DEPENDENCIES.read_text(encoding="utf-8")
    route_source = ROUTES.read_text(encoding="utf-8")

    assert "require_logo_upload_permission = _require_any(PERMISSION_CREATE, PERMISSION_UPDATE)" in dependency_source
    assert "auth: AuthContext = Depends(require_logo_upload_permission)" in route_source


def test_template_create_and_update_keep_dedicated_permissions():
    route_source = ROUTES.read_text(encoding="utf-8")

    assert "auth: AuthContext = Depends(require_create_permission)" in route_source
    assert "auth: AuthContext = Depends(require_update_permission)" in route_source
