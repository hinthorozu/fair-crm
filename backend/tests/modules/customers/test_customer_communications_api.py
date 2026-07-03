def test_create_customer_with_phone_email_website_collections(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={
            "display_name": "Multi Comm Co",
            "phones": [
                {"phone": "0212 555 0101", "is_primary": False},
                {"phone": "0532 555 0102", "is_primary": True},
            ],
            "emails": [
                {"email": "info@example.com", "is_primary": True},
                {"email": "export@example.com", "is_primary": False},
            ],
            "websites": [
                {"website": "https://primary.example.com", "is_primary": True},
                {"website": "https://secondary.example.com", "is_primary": False},
            ],
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["phone"] == "905325550102"
    assert body["email"] == "info@example.com;export@example.com"
    assert body["website"] == "primary.example.com"
    assert len(body["phones"]) == 2
    assert body["phones"][0]["phone"] == "905325550102"
    assert body["phones"][0]["is_primary"] is True
    assert len(body["emails"]) == 2
    assert body["emails"][0]["email"] == "info@example.com"
    assert len(body["websites"]) == 2
    assert body["websites"][0]["website"] == "primary.example.com"


def test_update_customer_with_phone_collection(client, auth_headers):
    create_response = client.post(
        "/api/v1/customers",
        json={"display_name": "Phone Update Co", "phone": "0212 555 0199"},
        headers=auth_headers,
    )
    customer_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={
            "phones": [
                {"phone": "0212 555 0200", "is_primary": False},
                {"phone": "0532 555 0201", "is_primary": True},
            ]
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["phone"] == "905325550201"
    assert len(body["phones"]) == 2
    assert body["phones"][0]["is_primary"] is True
    assert body["phones"][0]["phone"] == "905325550201"
