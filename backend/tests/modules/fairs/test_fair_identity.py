import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import canonicalize_fair_name, compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository


def _migration():
    path = Path(__file__).resolve().parents[3] / "alembic" / "versions" / "0090_system_fair_identity.py"
    spec = importlib.util.spec_from_file_location("migration_0090_system_fair_identity", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _system_fair(*, source: str, external_id: str) -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name="System Fair",
        organizer=None,
        venue="Venue",
        city="Ankara",
        country=None,
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name="system fair",
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source=source,
        external_id=external_id,
    )


def test_canonicalize_fair_name_uses_turkish_uppercase():
    assert canonicalize_fair_name("istanbul") == "İSTANBUL"
    assert canonicalize_fair_name("izmir") == "İZMİR"
    assert canonicalize_fair_name("ışık") == "IŞIK"
    assert canonicalize_fair_name("çiçek") == "ÇİÇEK"
    assert canonicalize_fair_name("şeker") == "ŞEKER"
    assert canonicalize_fair_name("öğütme") == "ÖĞÜTME"
    mixed = "İstanbul mobilya fuarı"
    canonical = canonicalize_fair_name(mixed)
    assert canonical == "İSTANBUL MOBİLYA FUARI"
    assert compute_normalized_name(name=mixed) == compute_normalized_name(name=canonical)


def test_organization_fair_create_stores_full_long_name(db_session, organization_id):
    now = datetime.now(tz=UTC)
    long_name = "ç" + ("ı" * 410)
    fair = Fair.create(organization_id=organization_id, name=long_name, now=now)
    saved = SqlAlchemyFairRepository(db_session).add(fair)
    db_session.expire_all()
    loaded = db_session.get(FairModel, saved.id)
    assert loaded.name == long_name
    assert len(loaded.name) == 411


def test_organization_fair_create_keeps_origin_and_organization(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = Fair.create(organization_id=organization_id, name="Customer Fair", now=now)
    saved = SqlAlchemyFairRepository(db_session).add(fair)

    assert saved.origin == "organization"
    assert saved.organization_id == organization_id
    assert saved.source is None
    assert saved.external_id is None


def test_system_fair_persists_with_null_organization(db_session):
    fair = _system_fair(source="tobb", external_id="fp-1")
    saved = SqlAlchemyFairRepository(db_session).add(fair)
    loaded = model_to_entity(db_session.get(FairModel, saved.id))

    assert loaded.origin == "system"
    assert loaded.organization_id is None
    assert loaded.source == "tobb"
    assert loaded.external_id == "fp-1"


def test_organization_origin_rejects_null_organization_id(db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = Fair.create(organization_id=organization_id, name="Broken Org", now=now)
    model = entity_to_model(fair)
    model.organization_id = None
    db_session.begin_nested()
    db_session.add(model)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_system_origin_rejects_organization_id(db_session, organization_id):
    fair = _system_fair(source="tobb", external_id="fp-2")
    model = entity_to_model(fair)
    model.organization_id = organization_id
    db_session.begin_nested()
    db_session.add(model)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_system_external_identity_is_unique(db_session):
    repo = SqlAlchemyFairRepository(db_session)
    repo.add(_system_fair(source="tobb", external_id="same"))
    db_session.begin_nested()
    with pytest.raises(IntegrityError):
        repo.add(_system_fair(source="tobb", external_id="same"))
    db_session.rollback()


def test_mapper_round_trip_keeps_identity_fields():
    fair = _system_fair(source="tobb", external_id="fp-3")
    restored = model_to_entity(entity_to_model(fair))

    assert restored.origin == "system"
    assert restored.organization_id is None
    assert restored.source == "tobb"
    assert restored.external_id == "fp-3"


def test_update_mapper_does_not_change_origin_or_organization(organization_id):
    fair = _system_fair(source="tobb", external_id="fp-4")
    fair.organization_id = organization_id
    fair.origin = "organization"
    model = entity_to_model(fair)
    fair.organization_id = None
    fair.origin = "system"
    fair.name = "Renamed"

    update_model_from_entity(model, fair)

    assert model.organization_id == organization_id
    assert model.origin == "organization"
    assert model.name == "Renamed"
    assert model.source == "tobb"
    assert model.external_id == "fp-4"


def test_migration_upgrade_downgrade_preserves_organization_fair(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fairs.db'}")
    organization_id = str(uuid4())
    fair_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE crm_fairs (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    organization_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    organizer VARCHAR(255),
                    venue VARCHAR(255),
                    city VARCHAR(100),
                    country VARCHAR(100),
                    start_date DATE,
                    end_date DATE,
                    website VARCHAR(255),
                    status VARCHAR(32) NOT NULL,
                    description TEXT,
                    normalized_name VARCHAR(500) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    deleted_at DATETIME,
                    archived_from_status VARCHAR(32),
                    adapter_key VARCHAR(100),
                    source_url TEXT,
                    scraper_config JSON
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO crm_fairs (
                    id, organization_id, name, status, normalized_name, created_at, updated_at
                ) VALUES (
                    :id, :organization_id, 'Existing', 'planned', 'existing', :now, :now
                )
                """
            ),
            {"id": fair_id, "organization_id": organization_id, "now": "2026-09-30T00:00:00"},
        )

    migration = _migration()
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT origin, organization_id, source, external_id FROM crm_fairs WHERE id = :id"),
            {"id": fair_id},
        ).one()
        assert row.origin == "organization"
        assert row.organization_id == organization_id
        assert row.source is None
        assert row.external_id is None
        checks = {
            item["name"]
            for item in inspect(connection).get_check_constraints("crm_fairs")
        }
        indexes = {item["name"] for item in inspect(connection).get_indexes("crm_fairs")}
        assert "ck_crm_fairs_origin_organization" in checks
        assert "uq_crm_fairs_system_external_id" in indexes

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.downgrade()
            migration.upgrade()

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT origin, organization_id FROM crm_fairs WHERE id = :id"),
            {"id": fair_id},
        ).one()
        assert row.origin == "organization"
        assert row.organization_id == organization_id
