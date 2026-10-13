from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.fairs.infrastructure.persistence.models import FairModel, TobbFairReviewModel
from app.modules.fairs.infrastructure.tobb_review_repository import SqlAlchemyTobbReviewRepository, TobbReviewConflict


def _fair(session, external_id="2026:1"):
    now = datetime.now(UTC)
    fair = FairModel(id=uuid4(), origin="system", organization_id=None, source="tobb", external_id=external_id,
                     name="AMBALAJ", normalized_name="31 AMBALAJ FUARI", identity_name="AMBALAJ FUARI",
                     city="İstanbul", organizer="Mevcut", status="planned", start_date=date(2026, 10, 20),
                     end_date=date(2026, 10, 23), created_at=now, updated_at=now,
                     adapter_key="keep", source_url="https://example.com/participants", scraper_config={"max_pages": 2})
    session.add(fair)
    session.flush()
    return fair


def _propose(repo, fair, start="2026-11-11", end="2026-11-14"):
    return repo.propose(kind="dates", fair_id=fair.id, name=fair.name,
                        stored={"start_date": fair.start_date.isoformat(), "end_date": fair.end_date.isoformat(),
                                "_date_revision": fair.tobb_date_revision},
                        proposed={"start_date": start, "end_date": end}, source={"city": "İstanbul", "name": "31 AMBALAJ FUARI"})


def test_date_rejection_is_durable_until_source_or_manual_baseline_changes(db_session):
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    row = repo.list_pending()[0]
    repo.decide(row["id"], version=row["version"], decision="keep", user_id=uuid4())
    assert repo.list_pending() == []
    assert not _propose(repo, fair)
    assert repo.list_pending() == []
    assert _propose(repo, fair, start="2026-11-12")
    changed = repo.list_pending()[0]
    assert changed["id"] != row["id"]
    repo.decide(changed["id"], version=changed["version"], decision="keep", user_id=uuid4())
    fair.start_date = date(2026, 10, 21)
    assert _propose(repo, fair, start="2026-11-12")
    assert len(repo.list_pending()) == 1


def test_updated_proposal_and_second_decision_reject_stale_version(db_session):
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    stale = repo.list_pending()[0]
    _propose(repo, fair, start="2026-11-12")
    current = repo.list_pending()[0]
    assert current["id"] == stale["id"] and current["version"] > stale["version"]
    with pytest.raises(TobbReviewConflict):
        repo.decide(stale["id"], version=stale["version"], decision="apply", user_id=uuid4())
    repo.decide(current["id"], version=current["version"], decision="apply", user_id=uuid4())
    assert (fair.start_date, fair.end_date) == (date(2026, 11, 12), date(2026, 11, 14))
    assert (fair.name, fair.organizer, fair.adapter_key, fair.scraper_config) == ("AMBALAJ", "Mevcut", "keep", {"max_pages": 2})
    with pytest.raises(TobbReviewConflict) as exc:
        repo.decide(current["id"], version=current["version"], decision="keep", user_id=uuid4())
    assert exc.value.current["status"] == "approved"


@pytest.mark.parametrize("start,end", [(None, "2026-11-14"), ("2026-11-11", None), ("2026-11-15", "2026-11-14")])
def test_invalid_dates_remain_pending_without_partial_update(db_session, start, end):
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair, start=start, end=end)
    row = repo.list_pending()[0]
    with pytest.raises(ValueError):
        repo.decide(row["id"], version=row["version"], decision="apply", user_id=uuid4())
    assert (fair.start_date, fair.end_date) == (date(2026, 10, 20), date(2026, 10, 23))
    assert repo.list_pending()[0]["status"] == "pending"


def test_manual_edit_rejects_an_old_screen(db_session):
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    row = repo.list_pending()[0]
    fair.start_date = date(2026, 10, 21)
    with pytest.raises(TobbReviewConflict):
        repo.decide(row["id"], version=row["version"], decision="apply", user_id=uuid4())
    assert len(repo.list_pending()) == 1


def test_manual_restore_of_original_dates_reopens_an_approved_identical_source(db_session):
    from app.modules.fairs.infrastructure.persistence.mappers import model_to_entity
    from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    row = repo.list_pending()[0]
    repo.decide(row["id"], version=row["version"], decision="apply", user_id=uuid4())
    manual = model_to_entity(fair)
    manual.update_fields(start_date=date(2026, 10, 20), end_date=date(2026, 10, 23), now=datetime.now(UTC))
    SqlAlchemyFairRepository(db_session).update(manual)
    assert fair.tobb_date_revision == 1
    assert _propose(repo, fair)
    assert len(repo.list_pending()) == 1


def test_unrelated_manual_field_edit_does_not_reopen_rejected_identical_dates(db_session):
    from app.modules.fairs.infrastructure.persistence.mappers import model_to_entity
    from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    row = repo.list_pending()[0]
    repo.decide(row["id"], version=row["version"], decision="keep", user_id=uuid4())
    manual = model_to_entity(fair)
    manual.update_fields(organizer="Manual organizer", now=datetime.now(UTC))
    SqlAlchemyFairRepository(db_session).update(manual)
    assert fair.tobb_date_revision == 0
    assert not _propose(repo, fair)


def test_deferred_name_mapping_is_durable_and_correctable_without_fair_moves(db_session):
    from app.modules.fairs.domain.services.normalizers import fair_city_key
    fair = _fair(db_session)
    target = _fair(db_session, "2026:2")
    target.name = "Diğer fuar"
    repo = SqlAlchemyTobbReviewRepository(db_session)
    source = {"identity_name": "AMBALAJ FUARI", "city": "İstanbul", "external_id": "2027:3"}
    repo.propose(kind="name", fair_id=None, name="AMBALAJ FUARI", stored={}, proposed={}, source=source)
    row = repo.list_pending()[0]
    actor = uuid4()
    repo.decide(row["id"], version=row["version"], decision="defer", user_id=actor)
    assert repo.list_pending()[0]["id"] == row["id"]
    repo.decide(row["id"], version=row["version"], decision="map", target_fair_id=fair.id, user_id=actor)
    assert repo.mapped_fair_id(source["identity_name"], fair_city_key(source["city"])) == fair.id
    mapping = repo.list_mappings()[0]
    repo.change_mapping(UUID(mapping["id"]), fair_id=target.id, user_id=actor)
    assert repo.mapped_fair_id(source["identity_name"], fair_city_key(source["city"])) == target.id
    assert fair.name == "AMBALAJ" and fair.external_id == "2026:1"
    assert target.name == "Diğer fuar" and target.external_id == "2026:2"


@pytest.mark.parametrize("end", [None, date(2026, 10, 12), date(2026, 10, 13)])
def test_manual_edition_selection_cannot_bypass_expiry_lock(db_session, end):
    fair = _fair(db_session)
    fair.end_date = end
    repo = SqlAlchemyTobbReviewRepository(db_session)
    source = {"identity_name": "AMBALAJ FUARI", "normalized_name": "32 AMBALAJ FUARI",
              "external_id": "2027:3", "start_date": "2027-11-11", "end_date": "2027-11-14"}
    repo.propose(kind="edition", fair_id=fair.id, name=fair.name, stored={}, proposed={}, source=source)
    row = repo.list_pending()[0]
    with pytest.raises(ValueError):
        repo.decide(row["id"], version=row["version"], decision="select", user_id=uuid4(), today=date(2026, 10, 12))
    assert fair.start_date == date(2026, 10, 20) and fair.end_date == end
    assert len(repo.list_pending()) == 1


def test_metadata_decisions_are_independent_from_dates_and_other_fields(db_session):
    fair = _fair(db_session)
    repo = SqlAlchemyTobbReviewRepository(db_session)
    _propose(repo, fair)
    for kind, incoming in [("organizer", "Yeni"), ("venue", "Yeni yer"), ("website", "fair.example")]:
        repo.propose(kind=kind, fair_id=fair.id, name=fair.name, stored={kind: getattr(fair, kind)},
                     proposed={kind: incoming}, source={})
    for row in repo.list_pending():
        if row["kind"] != "dates":
            repo.decide(row["id"], version=row["version"], decision="keep" if row["kind"] == "venue" else "apply", user_id=uuid4())
    assert (fair.organizer, fair.venue, fair.website) == ("Yeni", None, "fair.example")
    assert fair.start_date == date(2026, 10, 20) and fair.end_date == date(2026, 10, 23)
    assert repo.list_pending()[0]["kind"] == "dates"
