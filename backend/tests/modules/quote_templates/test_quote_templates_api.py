from uuid import UUID

from sqlalchemy import select

from app.modules.quote_templates.infrastructure.models import QuoteTemplateVersionModel


def test_update_creates_new_version_and_preserves_old(client, auth_headers, db_session):
    created = client.post(
        "/api/v1/quote-templates",
        headers=auth_headers,
        json={"name": "Standart Teklif", "logo_url": "/logo/one.png", "source_code": "<html>v1</html>"},
    )
    assert created.status_code == 201
    first = created.json()

    updated = client.patch(
        f"/api/v1/quote-templates/{first['id']}",
        headers=auth_headers,
        json={"name": "Standart Teklif", "logo_url": "/logo/two.png", "source_code": "<html>v2</html>"},
    )
    assert updated.status_code == 200
    second = updated.json()
    assert second["version_number"] == 2
    assert second["current_version_id"] != first["current_version_id"]

    versions = db_session.scalars(
        select(QuoteTemplateVersionModel).where(QuoteTemplateVersionModel.template_id == UUID(first["id"]))
    ).all()
    assert [(item.version_number, item.source_code) for item in versions] == [
        (1, "<html>v1</html>"),
        (2, "<html>v2</html>"),
    ]


def test_list_is_organization_scoped(client, auth_headers, other_organization_id, user_id):
    assert client.post(
        "/api/v1/quote-templates", headers=auth_headers,
        json={"name": "Organization One", "source_code": "<html></html>"},
    ).status_code == 201
    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    response = client.get("/api/v1/quote-templates", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
