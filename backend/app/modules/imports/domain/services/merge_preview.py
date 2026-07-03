"""Field-level merge preview for Smart Import Wizard (no CRM writes)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.modules.contacts.domain.entities import Contact
from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.shared.email import normalize_email_field

MergeOutcome = Literal[
    "same",
    "new",
    "will_add",
    "will_update",
    "will_keep",
    "conflict",
    "empty",
    "skipped",
]

CUSTOMER_FIELDS: list[tuple[str, str, str]] = [
    ("display_name", "company_name", "Firma"),
    ("phone", "phone", "Telefon"),
    ("email", "email", "Email"),
    ("website", "website", "Website"),
    ("country", "country", "Ülke"),
    ("city", "city", "Şehir"),
    ("address", "address", "Adres"),
    ("tax_number", "tax_number", "Vergi No"),
]

PARTICIPATION_FIELDS: list[tuple[str, str, str]] = [
    ("hall", "hall", "Salon"),
    ("stand", "stand", "Stand"),
    ("participation_status", "participation_status", "Katılım Durumu"),
    ("notes", "notes", "Notlar"),
]

CONTACT_FIELDS: list[tuple[str, str, str]] = [
    ("first_name", "contact_first_name", "Ad"),
    ("last_name", "contact_last_name", "Soyad"),
    ("title", "contact_title", "Ünvan"),
    ("email", "contact_email", "E-posta"),
    ("phone", "contact_phone", "Telefon"),
]

OUTCOME_LABELS: dict[str, str] = {
    "same": "Aynı",
    "new": "Yeni",
    "will_add": "Eklenecek",
    "will_update": "Güncellenecek",
    "will_keep": "Korunacak",
    "conflict": "Çakışıyor",
    "empty": "Boş",
    "skipped": "Atlanacak",
}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    return not str(value).strip()


def _display(value: Any) -> str | None:
    if _is_empty(value):
        return None
    return str(value).strip()


def _merge_email_preview(existing: str | None, incoming: str | None) -> tuple[str | None, str | None, str | None, MergeOutcome]:
    db = _display(existing)
    inc = _display(incoming)

    if _is_empty(incoming):
        if _is_empty(existing):
            return None, None, None, "empty"
        return db, None, db, "will_keep"

    if _is_empty(existing):
        try:
            result = normalize_email_field(str(incoming))
        except ValueError:
            result = inc
        return None, inc, result, "will_add"

    try:
        merged = normalize_email_field(f"{existing};{incoming}")
        existing_norm = normalize_email_field(existing) or ""
    except ValueError:
        return db, inc, db, "conflict"

    existing_set = set(existing_norm.split(";")) if existing_norm else set()
    try:
        incoming_norm = normalize_email_field(str(incoming)) or ""
    except ValueError:
        return db, inc, db, "conflict"
    incoming_set = set(incoming_norm.split(";")) if incoming_norm else set()

    if merged == existing_norm:
        if inc == db:
            return db, inc, merged, "same"
        return db, inc, merged, "will_keep"

    if incoming_set - existing_set:
        return db, inc, merged, "will_update"
    return db, inc, merged, "same"


def _scalar_merge_preview(
    db_value: Any,
    in_value: Any,
    *,
    is_create: bool,
    is_skipped: bool,
) -> tuple[str | None, str | None, str | None, MergeOutcome]:
    db = _display(db_value)
    inc = _display(in_value)

    if is_skipped:
        return db, inc, db, "skipped"

    if is_create:
        if _is_empty(inc):
            return None, None, None, "empty"
        return None, inc, inc, "new"

    if _is_empty(db) and _is_empty(inc):
        return None, None, None, "empty"
    if _is_empty(db) and not _is_empty(inc):
        return None, inc, inc, "will_add"
    if not _is_empty(db) and _is_empty(inc):
        return db, None, db, "will_keep"
    if db == inc:
        return db, inc, db, "same"
    return db, inc, db, "conflict"


def _customer_incoming_phone(data: dict[str, Any]) -> str | None:
    return _display(data.get("phone") or data.get("mobile_phone"))


def _has_contact_fields(data: dict[str, Any]) -> bool:
    keys = (
        "contact_first_name",
        "contact_last_name",
        "contact_title",
        "contact_department",
        "contact_email",
        "contact_phone",
        "contact_mobile_phone",
    )
    return any(not _is_empty(data.get(k)) for k in keys)


def _participation_status_label(status: Any) -> str | None:
    if status is None:
        return None
    return str(status.value if hasattr(status, "value") else status)


def effective_decision_for_preview(row: ImportRow) -> ImportDecision | None:
    if row.decision is not None:
        return row.decision
    if row.status == ImportRowStatus.INVALID:
        return ImportDecision.SKIP
    if row.status == ImportRowStatus.READY_TO_CREATE:
        return ImportDecision.CREATE_NEW
    if row.status in (ImportRowStatus.READY_TO_UPDATE, ImportRowStatus.POSSIBLE_DUPLICATE):
        return ImportDecision.UPDATE_EXISTING
    return None


def build_merge_preview(
    row: ImportRow,
    *,
    customer: Customer | None,
    customer_phone: str | None = None,
    customer_email: str | None = None,
    customer_website: str | None = None,
    participation: CustomerFairParticipation | None,
    contact: Contact | None,
    fair_id: UUID | None,
) -> dict[str, Any]:
    data = row.normalized_data_json or {}
    decision = effective_decision_for_preview(row)
    is_skipped = decision == ImportDecision.SKIP or row.status == ImportRowStatus.INVALID
    is_create = (
        not is_skipped
        and decision == ImportDecision.CREATE_NEW
        and row.status != ImportRowStatus.INVALID
    )
    is_update = (
        not is_skipped
        and decision == ImportDecision.UPDATE_EXISTING
        and customer is not None
    )
    applies = is_create or is_update

    groups: list[dict[str, Any]] = []

    customer_fields: list[dict[str, Any]] = []
    for db_key, in_key, label in CUSTOMER_FIELDS:
        if db_key == "phone":
            db_val = customer_phone if customer else None
            in_val = _customer_incoming_phone(data)
        elif db_key == "display_name":
            db_val = customer.display_name if customer else None
            in_val = data.get("company_name")
        elif db_key == "email":
            db_val = customer_email if customer else None
            in_val = data.get(in_key)
        elif db_key == "website":
            db_val = customer_website if customer else None
            in_val = data.get(in_key)
        else:
            db_val = getattr(customer, db_key, None) if customer else None
            in_val = data.get(in_key)

        if db_key == "email" and applies and not is_skipped:
            if is_create:
                crm, imp, res, outcome = _scalar_merge_preview(None, in_val, is_create=True, is_skipped=False)
            else:
                crm, imp, res, outcome = _merge_email_preview(
                    customer_email if customer else None,
                    in_val,
                )
        else:
            crm, imp, res, outcome = _scalar_merge_preview(
                db_val,
                in_val,
                is_create=is_create,
                is_skipped=is_skipped or not applies,
            )

        if _is_empty(in_val) and _is_empty(db_val) and outcome == "empty" and not applies:
            continue
        customer_fields.append(
            {
                "field_key": in_key,
                "label": label,
                "crm_value": crm,
                "import_value": imp,
                "result_value": res,
                "outcome": outcome,
                "outcome_label": OUTCOME_LABELS[outcome],
            }
        )

    if customer_fields:
        groups.append(
            {
                "entity": "customer",
                "entity_label": "Müşteri",
                "fields": customer_fields,
            }
        )

    if fair_id is not None and applies:
        participation_fields: list[dict[str, Any]] = []
        for db_key, in_key, label in PARTICIPATION_FIELDS:
            if db_key == "participation_status":
                db_val = _participation_status_label(participation.participation_status) if participation else None
                in_val = "exhibitor" if is_create and not participation else None
            else:
                db_val = getattr(participation, db_key, None) if participation else None
                in_val = data.get(in_key)

            crm, imp, res, outcome = _scalar_merge_preview(
                db_val,
                in_val,
                is_create=is_create and participation is None,
                is_skipped=is_skipped,
            )
            if db_key == "participation_status" and participation is None and is_create:
                outcome = "new" if not _is_empty(in_val) else "will_add"
                res = in_val or "exhibitor"

            participation_fields.append(
                {
                    "field_key": in_key,
                    "label": label,
                    "crm_value": crm,
                    "import_value": imp,
                    "result_value": res,
                    "outcome": outcome,
                    "outcome_label": OUTCOME_LABELS[outcome],
                }
            )
        groups.append(
            {
                "entity": "participation",
                "entity_label": "Fuar Katılımı",
                "fields": participation_fields,
            }
        )

    if _has_contact_fields(data) and applies:
        contact_fields: list[dict[str, Any]] = []
        for db_key, in_key, label in CONTACT_FIELDS:
            db_val = getattr(contact, db_key, None) if contact else None
            in_val = data.get(in_key)
            if db_key == "email" and contact and is_update:
                crm, imp, res, outcome = _merge_email_preview(contact.email, in_val)
            else:
                crm, imp, res, outcome = _scalar_merge_preview(
                    db_val,
                    in_val,
                    is_create=is_create or contact is None,
                    is_skipped=is_skipped,
                )
            contact_fields.append(
                {
                    "field_key": in_key,
                    "label": label,
                    "crm_value": crm,
                    "import_value": imp,
                    "result_value": res,
                    "outcome": outcome,
                    "outcome_label": OUTCOME_LABELS[outcome],
                }
            )
        groups.append(
            {
                "entity": "contact",
                "entity_label": "İletişim Kişisi",
                "fields": contact_fields,
            }
        )

    summary_lines = _build_summary_lines(groups, is_skipped=is_skipped)
    return {"groups": groups, "summary_lines": summary_lines}


def _build_summary_lines(groups: list[dict[str, Any]], *, is_skipped: bool) -> list[str]:
    if is_skipped:
        return ["✓ Bu satır atlanacak; CRM kayıtları değiştirilmeyecek."]

    lines: list[str] = []
    for group in groups:
        for field in group["fields"]:
            label = field["label"]
            outcome = field["outcome"]
            if outcome in ("new", "will_add"):
                if label.lower() == "email":
                    lines.append("✓ E-posta eklenecek")
                else:
                    lines.append(f"✓ {label} eklenecek")
            elif outcome == "will_update":
                if label.lower() == "email":
                    lines.append("✓ E-posta güncellenecek (birleştirme)")
                else:
                    lines.append(f"✓ {label} güncellenecek")
            elif outcome in ("will_keep", "same", "conflict") and field.get("crm_value"):
                lines.append(f"✓ {label} korunacak")

    if not lines:
        return ["✓ Bu satır için uygulanabilir alan değişikliği yok."]

    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(line)
    return deduped


def row_matches_filter(row: ImportRow, filter_key: str | None) -> bool:
    if not filter_key or filter_key == "all":
        return True
    if filter_key == "pending":
        return is_row_pending(row)
    if filter_key == "new":
        return row.status == ImportRowStatus.READY_TO_CREATE
    if filter_key == "will_update":
        return row.status in (ImportRowStatus.READY_TO_UPDATE, ImportRowStatus.POSSIBLE_DUPLICATE)
    if filter_key == "duplicate":
        return row.status == ImportRowStatus.POSSIBLE_DUPLICATE
    if filter_key == "invalid":
        return row.status == ImportRowStatus.INVALID
    if filter_key == "skip":
        return row.decision == ImportDecision.SKIP
    if filter_key == "applied":
        return False
    return True


def is_row_pending(row: ImportRow) -> bool:
    """Remaining rows in crm_import_rows are the active decision queue."""
    return True


DECISION_FILTER_COUNT_KEYS: tuple[str, ...] = (
    "pending",
    "all",
    "applied",
    "new",
    "will_update",
    "duplicate",
    "invalid",
    "skip",
)


def compute_decision_filter_counts(
    rows: list[ImportRow],
    *,
    batch: ImportBatch | None = None,
) -> dict[str, int]:
    counts = {
        key: sum(1 for row in rows if row_matches_filter(row, key))
        for key in DECISION_FILTER_COUNT_KEYS
        if key not in {"applied", "pending", "all"}
    }
    counts["pending"] = len(rows)
    counts["all"] = len(rows)
    if batch is not None:
        counts["applied"] = batch.created_rows + batch.updated_rows + batch.skipped_rows
    else:
        counts["applied"] = 0
    return counts


def sort_rows(
    rows: list[ImportRow],
    *,
    sort_by: str | None,
    sort_dir: str,
) -> list[ImportRow]:
    reverse = sort_dir.lower() == "desc"

    def company_name(r: ImportRow) -> str:
        return str((r.normalized_data_json or {}).get("company_name") or "").lower()

    def confidence(r: ImportRow) -> int:
        return r.match_confidence if r.match_confidence is not None else -1

    if sort_by == "company_name":
        return sorted(rows, key=company_name, reverse=reverse)
    if sort_by == "confidence":
        return sorted(rows, key=confidence, reverse=reverse)
    if sort_by == "status":
        return sorted(rows, key=lambda r: r.status.value, reverse=reverse)
    if sort_by == "row_number" or sort_by is None:
        return sorted(rows, key=lambda r: r.row_number, reverse=reverse)
    return sorted(rows, key=lambda r: r.row_number)
