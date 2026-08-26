from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel


def test_create_tag_then_content(client, auth_headers):
    tag_response = client.post("/api/v1/template-content-tags", headers=auth_headers, json={"name": "Teslimat"})
    assert tag_response.status_code == 201
    tag = tag_response.json()

    content_response = client.post("/api/v1/template-contents", headers=auth_headers, json={
        "tag_id": tag["id"], "title": "Teslimat Süresi",
    })
    assert content_response.status_code == 201
    assert content_response.json()["tag_name"] == "Teslimat"
    content = content_response.json()
    updated = client.patch(f"/api/v1/template-contents/{content['id']}", headers=auth_headers, json={"tag_id": tag["id"], "title": "Güncel Teslimat Süresi"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Güncel Teslimat Süresi"
    assert client.delete(f"/api/v1/template-content-tags/{tag['id']}", headers=auth_headers).status_code == 409
    assert client.delete(f"/api/v1/template-contents/{content['id']}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/v1/template-content-tags/{tag['id']}", headers=auth_headers).status_code == 204


def test_tag_is_organization_scoped(client, auth_headers, other_organization_id):
    tag = client.post("/api/v1/template-content-tags", headers=auth_headers, json={"name": "Ödeme"}).json()
    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    assert client.get("/api/v1/template-content-tags", headers=other_headers).json()["items"] == []
    response = client.post("/api/v1/template-contents", headers=other_headers, json={
        "tag_id": tag["id"], "title": "Ödeme",
    })
    assert response.status_code == 404


def test_list_contents_does_not_follow_foreign_tag(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
):
    now = datetime.now(tz=UTC)
    foreign_tag = TemplateContentTagModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="FOREIGN TAG",
        created_at=now,
        updated_at=now,
    )
    db_session.add(foreign_tag)
    db_session.flush()
    corrupt_owner_content = TemplateContentModel(
        id=uuid4(),
        organization_id=organization_id,
        tag_id=foreign_tag.id,
        title="Owner Content With Foreign Tag",
        created_at=now,
        updated_at=now,
    )
    db_session.add(corrupt_owner_content)
    db_session.commit()

    response = client.get("/api/v1/template-contents", headers=auth_headers)
    assert response.status_code == 200
    assert "FOREIGN TAG" not in response.text
    assert corrupt_owner_content.id not in {UUID(item["id"]) for item in response.json()["items"]}
