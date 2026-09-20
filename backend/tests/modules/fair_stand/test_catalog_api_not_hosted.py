def test_crm_openapi_does_not_host_fair_stand_api(client):
    paths = client.app.openapi()["paths"]
    hosted = [path for path in paths if path.startswith("/api/v1/fair-stand")]
    assert hosted == []


def test_crm_fair_stand_bootstrap_is_not_served(client, auth_headers):
    response = client.get("/api/v1/fair-stand/catalog/bootstrap", headers=auth_headers)
    assert response.status_code == 404
