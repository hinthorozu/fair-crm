"""Product-specific TOBB proposals; shares the existing system-fair review workflow."""
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from hashlib import sha256
from zoneinfo import ZoneInfo
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.modules.fairs.infrastructure.persistence.models import FairModel, TobbFairMappingModel, TobbFairReviewModel
from app.modules.fairs.domain.services.normalizers import fair_city_key, compute_identity_name
from app.modules.fairs.domain.services.normalizers import canonicalize_fair_name, system_fair_status_for_dates
from app.modules.fairs.domain.services.tobb_decisions import approved_dates, selected_edition_dates
from app.modules.fairs.domain.exceptions import TobbReviewConflict


def review_response(item: TobbFairReviewModel) -> dict:
    return {
        "id": str(item.id), "fair_id": str(item.fair_id) if item.fair_id else None,
        "kind": item.kind, "name": item.name, "status": item.status, "version": item.version,
        "stored_values": item.stored_values, "proposed_values": item.proposed_values,
        "source_row": item.source_row, "decision": item.decision,
        "decided_by": str(item.decided_by) if item.decided_by else None,
        "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat(),
    }


def fair_values(fair, fields: tuple[str, ...]) -> dict:
    return {field: (value.isoformat() if isinstance(value, date) else value)
            for field in fields for value in [getattr(fair, field)]}


class SqlAlchemyTobbReviewRepository:
    def __init__(self, session: Session):
        self.session = session

    @contextmanager
    def decision_transaction(self):
        try:
            with self.session.begin_nested():
                yield
        except SQLAlchemyError as exc:
            raise ValueError("Kayıt veritabanında uygulanamadı; yeniden deneyin") from exc

    def mapped_fair_id(self, identity: str, city: str) -> UUID | None:
        return self.session.scalar(select(TobbFairMappingModel.fair_id).where(
            TobbFairMappingModel.identity_name == identity, TobbFairMappingModel.city_key == city,
        ))

    def propose(self, *, kind: str, fair_id: UUID | None, name: str, stored: dict, proposed: dict, source: dict) -> bool:
        key = sha256(f"{fair_id or (compute_identity_name(name=name) + ':' + fair_city_key(source.get('city')))}:{kind}".encode()).hexdigest()
        item = self.session.scalar(select(TobbFairReviewModel).where(
            TobbFairReviewModel.review_key == key, TobbFairReviewModel.status == "pending",
        ).with_for_update())
        if item is not None:
            if item.stored_values != stored or item.proposed_values != proposed or item.source_row != source:
                item.stored_values, item.proposed_values, item.source_row = stored, proposed, source
                item.version += 1
                item.updated_at = datetime.now(UTC)
            return True
        previous = self.session.scalar(select(TobbFairReviewModel).where(
            TobbFairReviewModel.review_key == key,
        ).order_by(TobbFairReviewModel.created_at.desc()).limit(1))
        if (previous is not None and previous.status == "rejected"
                and previous.stored_values == stored and previous.proposed_values == proposed):
            return False
        now = datetime.now(UTC)
        self.session.add(TobbFairReviewModel(
            id=uuid4(), review_key=key, fair_id=fair_id, kind=kind, name=name, status="pending",
            version=1, stored_values=stored, proposed_values=proposed, source_row=source,
            created_at=now, updated_at=now,
        ))
        self.session.flush()
        return True

    def list_pending(self, *, search: str = "", kind: str | None = None) -> list[dict]:
        query = select(TobbFairReviewModel).where(TobbFairReviewModel.status == "pending")
        if search:
            query = query.where(TobbFairReviewModel.name.ilike(f"%{search}%"))
        if kind:
            query = query.where(TobbFairReviewModel.kind == kind)
        return [review_response(item) for item in self.session.scalars(query.order_by(
            TobbFairReviewModel.created_at, TobbFairReviewModel.id,
        )).all()]

    def decide(self, review_id: UUID | str, *, version: int, decision: str, user_id: UUID,
               target_fair_id: UUID | None = None, today: date | None = None,
               source_external_id: str | None = None) -> dict:
        review_id = UUID(str(review_id))
        item = self.session.scalar(select(TobbFairReviewModel).where(
            TobbFairReviewModel.id == review_id,
        ).with_for_update())
        if item is None:
            raise TobbReviewConflict("İnceleme bulunamadı")
        if item.status != "pending" or item.version != version:
            raise TobbReviewConflict("İnceleme değişti; güncel kaydı yeniden açın", review_response(item))
        if decision == "defer":
            return review_response(item)
        source = item.source_row
        if source.get("choices") and decision not in {"keep", "defer"}:
            chosen = [row for row in source["choices"] if row["external_id"] == source_external_id]
            if len(chosen) != 1:
                raise ValueError("İşlenecek TOBB edisyonunu seçin")
            source = chosen[0]
        fair = self.session.scalar(select(FairModel).where(
            FairModel.id == item.fair_id, FairModel.origin == "system", FairModel.deleted_at.is_(None),
        ).with_for_update()) if item.fair_id else None
        if item.kind in {"dates", "organizer", "venue", "website"}:
            fields = ("start_date", "end_date") if item.kind == "dates" else (item.kind,)
            current_values = fair_values(fair, fields) if fair is not None else {}
            if item.kind == "dates" and "_date_revision" in item.stored_values and fair is not None:
                current_values["_date_revision"] = fair.tobb_date_revision
            if fair is None or current_values != item.stored_values:
                raise TobbReviewConflict("Fuar değişti; yeniden senkronize edin", review_response(item))
            if decision not in {"apply", "keep"}:
                raise ValueError("Geçersiz karar")
            if decision == "apply":
                values = dict(item.proposed_values)
                if item.kind == "dates":
                    values = approved_dates(values)
                for field in fields:
                    setattr(fair, field, values[field])
                fair.updated_at = datetime.now(UTC)
        elif item.kind in {"name", "city", "edition"}:
            if decision == "keep":
                pass
            elif decision in {"map", "same"}:
                target = self.session.scalar(select(FairModel).where(
                    FairModel.id == (target_fair_id or item.fair_id),
                    FairModel.origin == "system", FairModel.deleted_at.is_(None),
                ).with_for_update())
                if target is None:
                    raise ValueError("Aktif sistem fuarı seçilmelidir")
                self._remember_mapping(source, target.id, user_id)
                if item.kind == "city" and decision == "same":
                    if target.city != item.stored_values.get("city"):
                        raise TobbReviewConflict("Şehir değişti; yeniden senkronize edin", review_response(item))
                    target.city = item.proposed_values["city"]
                    target.updated_at = datetime.now(UTC)
            elif decision == "select" and item.kind == "edition":
                current_day = today or datetime.now(ZoneInfo("Europe/Istanbul")).date()
                if fair is None:
                    raise ValueError("Mevcut edisyon bitmeden yeni edisyona geçilemez")
                dates = selected_edition_dates(fair.end_date, source, current_day)
                start, end = dates["start_date"], dates["end_date"]
                fair.start_date, fair.end_date = start, end
                fair.external_id = source["external_id"]
                fair.normalized_name = source["normalized_name"]
                fair.identity_name = source["identity_name"]
                fair.updated_at = datetime.now(UTC)
            elif decision in {"create", "different"} and item.kind in {"name", "city"}:
                start = date.fromisoformat(source["start_date"]) if source.get("start_date") else None
                end = date.fromisoformat(source["end_date"]) if source.get("end_date") else None
                if start and end and end < start:
                    raise ValueError("Bitiş tarihi başlangıçtan önce olamaz")
                now = datetime.now(UTC)
                held = self.session.scalar(select(FairModel.id).where(
                    FairModel.origin == "system", FairModel.source == "tobb",
                    FairModel.external_id == source["external_id"],
                ))
                target = FairModel(
                    id=uuid4(), origin="system", organization_id=None, source="tobb",
                    external_id=None if held else source["external_id"],
                    name=canonicalize_fair_name(source["name"]), normalized_name=source["normalized_name"],
                    identity_name=source["identity_name"], organizer=source.get("organizer"),
                    venue=source.get("venue"), website=source.get("website"), city=source.get("city"),
                    country="Türkiye", start_date=start, end_date=end,
                    status=(system_fair_status_for_dates(start_date=start, end_date=end, today=today or datetime.now(ZoneInfo("Europe/Istanbul")).date()) or "planned"),
                    created_at=now, updated_at=now,
                )
                self.session.add(target)
                self.session.flush()
                self._remember_mapping(source, target.id, user_id)
                item.fair_id = target.id
            else:
                raise ValueError("Bu öneri için geçersiz karar")
        else:
            raise ValueError("Bilinmeyen inceleme türü")
        item.status = "rejected" if decision == "keep" else "approved"
        item.decision, item.decided_by, item.decided_at = decision, user_id, datetime.now(UTC)
        item.updated_at = item.decided_at
        item.version += 1
        self.session.flush()
        return review_response(item)

    def _remember_mapping(self, source: dict, fair_id: UUID, user_id: UUID) -> None:
        identity, city = source["identity_name"], fair_city_key(source.get("city"))
        item = self.session.scalar(select(TobbFairMappingModel).where(
            TobbFairMappingModel.identity_name == identity, TobbFairMappingModel.city_key == city,
        ).with_for_update())
        if item is None:
            item = TobbFairMappingModel(id=uuid4(), identity_name=identity, city_key=city,
                                       fair_id=fair_id, decided_by=user_id, updated_at=datetime.now(UTC))
            self.session.add(item)
        else:
            item.fair_id, item.decided_by, item.updated_at = fair_id, user_id, datetime.now(UTC)

    def change_mapping(self, mapping_id: UUID, *, fair_id: UUID, user_id: UUID) -> None:
        target = self.session.get(FairModel, fair_id)
        if target is None or target.origin != "system" or target.deleted_at is not None:
            raise ValueError("Aktif sistem fuarı seçilmelidir")
        item = self.session.get(TobbFairMappingModel, mapping_id, with_for_update=True)
        if item is None:
            raise ValueError("Eşleştirme bulunamadı")
        item.fair_id, item.decided_by, item.updated_at = fair_id, user_id, datetime.now(UTC)

    def list_mappings(self) -> list[dict]:
        records = self.session.execute(select(TobbFairMappingModel, FairModel.name).join(
            FairModel, FairModel.id == TobbFairMappingModel.fair_id,
        ).order_by(TobbFairMappingModel.identity_name)).all()
        return [{"id": str(item.id), "identity_name": item.identity_name, "city": item.city_key,
                 "fair_id": str(item.fair_id), "name": name, "updated_at": item.updated_at.isoformat()}
                for item, name in records]
