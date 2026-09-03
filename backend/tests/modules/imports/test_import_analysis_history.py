"""Stale scraper analysis: reanalyze after another batch applied the same customer."""

from datetime import UTC, datetime
from uuid import uuid4

from tests.modules.imports.import_decision_helpers import set_decision_and_apply


def _create_fair(client, auth_headers, *, name: str) -> str:
    res = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={
            "name": name,
            "location": "Istanbul",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _canonical_batch(client, auth_headers, *, fair_id: str, company_name: str, run_suffix: str) -> str:
    run_id = str(uuid4())
    payload = {
        "source": {
            "type": "scraper",
            "adapter_key": "tuyap_new",
            "fair_id": fair_id,
            "run_id": run_id,
            "source_url": f"https://example.test/{run_suffix}",
        },
        "metadata": {
            "created_at": datetime(2026, 7, 10, 12, 0, tzinfo=UTC).isoformat(),
            "row_count": 1,
        },
        "rows": [
            {
                "company_name": company_name,
                "normalized_company_name": company_name.lower(),
                "emails": [],
                "phones": [],
                "country": "Türkiye",
                "raw": {},
            }
        ],
    }
    created = client.post("/api/v1/data-integration/imports/from-canonical", headers=auth_headers, json=payload)
    assert created.status_code == 201
    return created.json()["batch"]["id"]


def _wait_analyze_job(client, auth_headers, batch_id: str) -> None:
    analyze = client.post(
        f"/api/v1/data-integration/imports/{batch_id}/analyze-job",
        headers=auth_headers,
    )
    assert analyze.status_code == 202
    job_id = analyze.json()["job_id"]
    for _ in range(60):
        job = client.get(f"/api/v1/data-integration/jobs/{job_id}", headers=auth_headers)
        if job.json()["status"] in ("completed", "failed"):
            break
    assert job.json()["status"] == "completed"


def test_analyzed_at_set_on_successful_analyze(client, auth_headers):
    fair_id = _create_fair(client, auth_headers, name="Analyze At Fair")
    batch_id = _canonical_batch(client, auth_headers, fair_id=fair_id, company_name="Timestamp Co", run_suffix="ts")

    batch_before = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers).json()
    assert batch_before["analyzed_at"] is None

    _wait_analyze_job(client, auth_headers, batch_id)

    batch_after = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers).json()
    assert batch_after["status"] == "decision_required"
    assert batch_after["analyzed_at"] is not None

    first_analyzed_at = batch_after["analyzed_at"]
    _wait_analyze_job(client, auth_headers, batch_id)
    batch_re = client.get(f"/api/v1/data-integration/imports/{batch_id}", headers=auth_headers).json()
    assert batch_re["analyzed_at"] is not None
    assert batch_re["analyzed_at"] >= first_analyzed_at


def test_stale_scraper_batch_reanalyze_matches_customer_after_other_batch_applied(
    client, auth_headers, db_session
):
    fair_one = _create_fair(client, auth_headers, name="ABC Fair One")
    fair_two = _create_fair(client, auth_headers, name="ABC Fair Two")

    batch_one = _canonical_batch(
        client, auth_headers, fair_id=fair_one, company_name="ABC", run_suffix="b1"
    )
    batch_two = _canonical_batch(
        client, auth_headers, fair_id=fair_two, company_name="ABC", run_suffix="b2"
    )

    _wait_analyze_job(client, auth_headers, batch_two)
    rows_two = client.get(f"/api/v1/data-integration/imports/{batch_two}/rows", headers=auth_headers).json()["items"]
    assert rows_two[0]["status"] == "ready_to_create"

    _wait_analyze_job(client, auth_headers, batch_one)
    rows_one = client.get(f"/api/v1/data-integration/imports/{batch_one}/rows", headers=auth_headers).json()["items"]
    row_one_id = rows_one[0]["id"]
    set_decision_and_apply(
        client,
        auth_headers,
        batch_one,
        row_one_id,
        {"decision": "create_new"},
    )

    listing = client.get("/api/v1/data-integration/imports", headers=auth_headers).json()
    batch_two_item = next(item for item in listing["items"] if item["id"] == batch_two)
    assert batch_two_item["status"] == "decision_required"
    assert batch_two_item["analyzed_at"] is not None

    _wait_analyze_job(client, auth_headers, batch_two)
    rows_two_after = client.get(f"/api/v1/data-integration/imports/{batch_two}/rows", headers=auth_headers).json()["items"]
    row = rows_two_after[0]
    assert row["status"] == "ready_to_update"
    assert row["match_customer_id"] is not None
    assert row["participation_exists"] is False
    assert row["decision"] in ("update_existing", "participation_only")

    batch_two_after = client.get(f"/api/v1/data-integration/imports/{batch_two}", headers=auth_headers).json()
    assert batch_two_after["status"] == "decision_required"
    assert batch_two_after["analyzed_at"] is not None
