from uuid import uuid4

from app.modules.quote_templates.infrastructure import logo_storage


def test_logo_src_for_render_inlines_only_owned_managed_logo(monkeypatch, tmp_path):
    organization_id = uuid4()
    other_organization_id = uuid4()
    monkeypatch.setattr(logo_storage, "LOGO_STORAGE_ROOT", tmp_path)

    organization_dir = tmp_path / str(organization_id)
    organization_dir.mkdir(parents=True)
    logo_path = organization_dir / "logo.png"
    logo_path.write_bytes(b"owned-logo")
    logo_url = f"{logo_storage.LOGO_API_PREFIX}{organization_id}/logo.png"

    rendered = logo_storage.logo_src_for_render(logo_url, organization_id)
    assert rendered.startswith("data:image/png;base64,")
    assert logo_storage.LOGO_API_PREFIX not in rendered

    assert logo_storage.logo_src_for_render(logo_url, other_organization_id) == ""


def test_resolve_logo_file_rejects_traversal(monkeypatch, tmp_path):
    organization_id = uuid4()
    monkeypatch.setattr(logo_storage, "LOGO_STORAGE_ROOT", tmp_path)

    assert logo_storage.resolve_logo_file(organization_id, "../foreign.png") is None
    assert logo_storage.resolve_logo_file(organization_id, "not-an-image.txt") is None
