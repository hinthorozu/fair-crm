from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel


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


def test_list_does_not_follow_foreign_current_version(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
):
    created = client.post(
        "/api/v1/quote-templates",
        headers=auth_headers,
        json={"name": "Owner Template", "source_code": "<html>OWNER</html>"},
    )
    assert created.status_code == 201
    owner_template_id = UUID(created.json()["id"])

    now = datetime.now(tz=UTC)
    foreign_template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="FOREIGN TEMPLATE",
        created_at=now,
        updated_at=now,
    )
    db_session.add(foreign_template)
    db_session.flush()
    foreign_version = QuoteTemplateVersionModel(
        id=uuid4(),
        template_id=foreign_template.id,
        version_number=1,
        logo_url="/FOREIGN-logo.png",
        source_code="<html>FOREIGN VERSION SOURCE</html>",
        created_at=now,
    )
    db_session.add(foreign_version)
    db_session.flush()
    foreign_template.current_version_id = foreign_version.id

    owner_template = db_session.scalar(
        select(QuoteTemplateModel).where(
            QuoteTemplateModel.id == owner_template_id,
            QuoteTemplateModel.organization_id == organization_id,
        )
    )
    assert owner_template is not None
    owner_template.current_version_id = foreign_version.id
    db_session.commit()

    response = client.get("/api/v1/quote-templates", headers=auth_headers)
    assert response.status_code == 200
    assert "FOREIGN" not in response.text
    assert owner_template_id not in {UUID(item["id"]) for item in response.json()["items"]}
