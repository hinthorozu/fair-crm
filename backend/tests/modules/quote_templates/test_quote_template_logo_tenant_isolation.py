from app.modules.quote_templates.api import routes as quote_template_routes
from app.modules.quote_templates.infrastructure import logo_storage


def _use_logo_root(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(quote_template_routes, "LOGO_STORAGE_ROOT", tmp_path)
    monkeypatch.setattr(logo_storage, "LOGO_STORAGE_ROOT", tmp_path)


def test_managed_logo_asset_is_organization_scoped(
    client,
    auth_headers,
    other_organization_id,
    monkeypatch,
    tmp_path,
):
    _use_logo_root(monkeypatch, tmp_path)
    content = b"tenant-owned-logo-bytes"
    uploaded = client.post(
        "/api/v1/quote-templates/logo",
        headers=auth_headers,
        files={"file": ("logo.png", content, "image/png")},
    )
    assert uploaded.status_code == 200
    logo_url = uploaded.json()["url"]

    owned = client.get(logo_url, headers=auth_headers)
    assert owned.status_code == 200
    assert owned.content == content
    assert owned.headers["content-type"].startswith("image/png")

    foreign_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    foreign = client.get(logo_url, headers=foreign_headers)
    assert foreign.status_code == 404
    assert content not in foreign.content

    legacy_url = logo_url.replace(
        "/api/v1/data/quote-template-logos/",
        "/data/quote-template-logos/",
        1,
    )
    legacy = client.get(legacy_url, headers=auth_headers)
    assert legacy.status_code == 404


def test_template_write_rejects_foreign_managed_logo_pointer(
    client,
    auth_headers,
    other_organization_id,
):
    foreign_logo_url = (
        f"/api/v1/data/quote-template-logos/{other_organization_id}/foreign.png"
    )
    created = client.post(
        "/api/v1/quote-templates",
        headers=auth_headers,
        json={
            "name": "Cross Tenant Logo",
            "logo_url": foreign_logo_url,
            "source_code": "<html>{{logo_url}}</html>",
        },
    )
    assert created.status_code == 400
    assert created.json()["detail"] == "Logo bu organizasyona ait değil."
