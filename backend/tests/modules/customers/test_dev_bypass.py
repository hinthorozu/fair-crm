from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.modules.customers.api.dependencies import get_db


@pytest.fixture
def bypass_client(db_session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FAIR_CRM_DEV_BYPASS_CORE", "true")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    def override_get_db():
        try:
            yield db_session
            db_session.flush()
        except Exception:
            db_session.rollback()
            raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_dev_bypass_create_customer_without_jwt(bypass_client, organization_id):
    response = bypass_client.post(
        "/api/v1/customers",
        json={"display_name": "Bypass Customer"},
        headers={
            "Authorization": "Bearer dev-bypass",
            "X-Organization-Id": str(organization_id),
        },
    )
    assert response.status_code == 201
    assert response.json()["display_name"] == "Bypass Customer"


def test_dev_bypass_disabled_requires_auth(client, organization_id):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": "Should Fail"},
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401
