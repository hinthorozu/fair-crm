"""Canonical operation type catalog rows (idempotent seed helper)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.operations.infrastructure.persistence.models import OperationTypeModel


class OperationTypeCapabilitiesSeed(TypedDict):
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool


# Display metadata + capabilities mirrored from former type_registry definitions.
CANONICAL_OPERATION_TYPES: tuple[tuple[str, str, int, OperationTypeCapabilitiesSeed], ...] = (
    (
        "scraper",
        "Web Scraper",
        10,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": True,
            "supports_schedule": False,
            "supports_items": False,
        },
    ),
    (
        "email",
        "E-posta",
        20,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": True,
            "supports_items": True,
        },
    ),
    (
        "bulk_email",
        "Toplu E-posta",
        30,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": True,
            "supports_schedule": True,
            "supports_items": True,
        },
    ),
    (
        "enrichment",
        "Zenginleştirme",
        40,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": False,
            "supports_items": True,
        },
    ),
    (
        "duplicate_check",
        "Duplicate Kontrolü",
        50,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": False,
            "supports_items": True,
        },
    ),
    (
        "data_cleanup",
        "Veri Temizleme",
        60,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": False,
            "supports_items": True,
        },
    ),
    (
        "whatsapp",
        "WhatsApp",
        70,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": True,
            "supports_items": True,
        },
    ),
    (
        "manual_task",
        "Manuel Görev",
        80,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": True,
            "supports_items": False,
        },
    ),
    (
        "reminder",
        "Hatırlatma",
        90,
        {
            "supports_pause": False,
            "supports_resume": False,
            "supports_retry": False,
            "supports_schedule": True,
            "supports_items": True,
        },
    ),
)


def ensure_default_operation_types(session: Session) -> None:
    """Insert missing catalog rows; never overwrite existing names/flags/capabilities."""
    existing = {row.key for row in session.query(OperationTypeModel.key).all()}
    now = datetime.now(UTC)
    for key, name, sort_order, caps in CANONICAL_OPERATION_TYPES:
        if key in existing:
            continue
        session.add(
            OperationTypeModel(
                id=uuid4(),
                key=key,
                name=name,
                is_active=True,
                sort_order=sort_order,
                created_at=now,
                updated_at=now,
                **caps,
            )
        )
    session.flush()
