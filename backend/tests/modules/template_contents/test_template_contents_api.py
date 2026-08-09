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
