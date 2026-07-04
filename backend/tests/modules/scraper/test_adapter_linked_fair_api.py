"""Tests for adapter linked fairs API."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_list_adapter_linked_fairs_endpoint(client: TestClient, db_session, organization_id, auth_headers):
    now = datetime.now(UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Foodist Expo",
        organizer=None,
        venue="TÜYAP",
        city="İstanbul",
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.ACTIVE.value,
        description=None,
        normalized_name=compute_normalized_name(name="Foodist Expo"),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )
    db_session.add(fair)
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        started_at=now,
    )
    db_session.flush()

    response = client.get(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/fairs",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Foodist Expo"
    assert payload["items"][0]["city"] == "İstanbul"
    assert payload["items"][0]["source_url"] == "https://foodist.test/list"


def test_list_adapter_linked_fairs_unknown_adapter(client: TestClient, auth_headers):
    response = client.get("/api/v1/scraper/adapters/unknown/fairs", headers=auth_headers)
    assert response.status_code == 404
