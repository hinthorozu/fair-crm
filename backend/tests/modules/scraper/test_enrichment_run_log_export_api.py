"""Tests for enrichment run log export API."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.infrastructure.repositories.scraper_run_log_repository import ScraperRunLogRepository
from app.modules.scraper.services.enrichment_run_log_txt_formatter import build_console_txt_export
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _seed_fair(db_session, organization_id: UUID, *, name: str) -> FairModel:
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        normalized_name=name.lower(),
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def _seed_enrichment_run(
    db_session,
    organization_id: UUID,
    *,
    fair_id: UUID | None = None,
    fair_name: str | None = None,
    log_count: int = 3,
) -> tuple:
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    logs = ScraperRunLogService(ScraperRunLogRepository(db_session))
    started_at = datetime(2026, 7, 20, 16, 7, 24, tzinfo=UTC)
    resolved_fair_id = fair_id
    if fair_name is not None and resolved_fair_id is None:
        resolved_fair_id = _seed_fair(db_session, organization_id, name=fair_name).id
    run = history.start_run(
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        input_url=None,
        fair_name=fair_name,
        fair_year=2026 if fair_name else None,
        organization_id=organization_id,
        fair_id=resolved_fair_id,
        started_at=started_at,
        run_source=ScraperRunSource.ENRICHMENT,
    )
    created_logs = []
    for index in range(log_count):
        created_logs.append(
            logs.append_log(
                run_id=run.id,
                level=ScraperRunLogLevel.INFO,
                step="candidate_preview" if index > 0 else "candidates_to_process",
                message=f"{index}. ABC Gıda" if index > 0 else "50 firma işleme alınacak.",
                metadata={"customer_id": str(uuid4())} if index > 0 else None,
                created_at=started_at + timedelta(seconds=index),
            )
        )
    logs.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.SUCCESS,
        step="run_finished",
        message="Müşteri iletişim zenginleştirme tamamlandı",
        metadata={
            "customers_scanned": 50,
            "found": 36,
            "not_found": 10,
            "failed": 4,
            "dry_run": False,
            "import_batch_id": str(uuid4()),
            "import_batch_created": True,
        },
        created_at=started_at + timedelta(seconds=log_count),
    )
    finished_at = started_at + timedelta(minutes=4, seconds=39)
    history.complete_run(
        run.id,
        handoff=ScraperImportHandoff(canonical_rows=[{"company_name": "Demo"}]),
        finished_at=finished_at,
    )
    db_session.flush()
    return run, created_logs, resolved_fair_id


def test_export_txt_matches_run_detail_console_format(
    client: TestClient, db_session, organization_id, auth_headers
):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    logs = ScraperRunLogService(ScraperRunLogRepository(db_session))
    run = history.start_run(
        adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
        input_url=None,
        fair_name=None,
        fair_year=None,
        organization_id=organization_id,
        run_source=ScraperRunSource.ENRICHMENT,
    )
    created_at = datetime(2026, 7, 20, 20, 3, 13, tzinfo=UTC)
    seeded_logs = [
        logs.append_log(
            run_id=run.id,
            level=ScraperRunLogLevel.INFO,
            step="website_fetch_started",
            message="Sayfa isteniyor:\nhttps://example.test",
            created_at=created_at,
        ),
        logs.append_log(
            run_id=run.id,
            level=ScraperRunLogLevel.INFO,
            step="website_fetch_success",
            message="Sayfa alındı:\nhttps://example.test",
            created_at=created_at + timedelta(seconds=2),
        ),
        logs.append_log(
            run_id=run.id,
            level=ScraperRunLogLevel.INFO,
            step="email_found",
            message="E-posta bulundu: ABC Gıda",
            created_at=created_at + timedelta(seconds=4),
        ),
    ]
    db_session.flush()

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "txt"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.content.decode("utf-8")
    expected = build_console_txt_export(seeded_logs)
    assert body == expected
    assert "23:03:13 [Web sitesi taranıyor]" in body
    assert "Sayfa isteniyor:\nhttps://example.test" in body
    assert "23:03:17 [E-posta bulundu]" in body
    assert "ABC Gıda" in body
    assert "FAIR CRM - Enrichment Run Log" not in body


def test_export_json_is_parseable_with_full_timestamps(
    client: TestClient, db_session, organization_id, auth_headers
):
    run, _created_logs, _fair_id = _seed_enrichment_run(db_session, organization_id)

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = json.loads(response.content.decode("utf-8"))
    assert payload["run"]["scope"] == "org"
    assert payload["run"]["processed"] == 50
    assert len(payload["logs"]) == 4
    first = payload["logs"][0]
    assert set(first.keys()) == {"created_at", "level", "step", "message"}
    assert first["step"] == "candidates_to_process"
    assert first["created_at"].endswith("Z")


def test_export_org_wide_run_scope(client: TestClient, db_session, organization_id, auth_headers):
    run, _, _fair_id = _seed_enrichment_run(db_session, organization_id)

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = json.loads(response.content.decode("utf-8"))
    assert payload["run"]["scope"] == "org"


def test_export_fair_scoped_run_scope(client: TestClient, db_session, organization_id, auth_headers):
    run, _, fair_id = _seed_enrichment_run(
        db_session,
        organization_id,
        fair_name="Food İst",
    )

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = json.loads(response.content.decode("utf-8"))
    assert payload["run"]["scope"] == "fair"
    assert payload["run"]["fair_id"] == str(fair_id)
    assert payload["run"]["fair_name"] == "Food İst"


def test_export_includes_all_logs_when_more_than_page_size(
    client: TestClient, db_session, organization_id, auth_headers
):
    run, _, _fair_id = _seed_enrichment_run(db_session, organization_id, log_count=600)

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "json"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = json.loads(response.content.decode("utf-8"))
    assert len(payload["logs"]) == 601


def test_export_logs_are_ordered_chronologically(client: TestClient, db_session, organization_id, auth_headers):
    run, _, _fair_id = _seed_enrichment_run(db_session, organization_id, log_count=5)

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "json"},
        headers=auth_headers,
    )

    payload = json.loads(response.content.decode("utf-8"))
    timestamps = [item["created_at"] for item in payload["logs"]]
    assert timestamps == sorted(timestamps)
    assert payload["logs"][0]["message"] == "50 firma işleme alınacak."
    assert payload["logs"][-1]["step"] == "run_finished"


def test_export_rejects_invalid_format(client: TestClient, db_session, organization_id, auth_headers):
    run, _, _fair_id = _seed_enrichment_run(db_session, organization_id)

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "csv"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Desteklenmeyen format."


def test_export_not_visible_from_other_organization(
    client: TestClient,
    db_session,
    organization_id,
    other_organization_id,
    user_id,
):
    run, _, _fair_id = _seed_enrichment_run(db_session, organization_id)
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "txt"},
        headers=other_headers,
    )

    assert response.status_code == 404


def test_export_rejects_non_enrichment_run(client: TestClient, db_session, organization_id, auth_headers):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        organization_id=organization_id,
    )
    db_session.flush()

    response = client.get(
        f"/api/v1/scraper/runs/{run.id}/logs/export",
        params={"format": "txt"},
        headers=auth_headers,
    )

    assert response.status_code == 404
