"""Pure TOBB review invariants shared by persistence decisions and tests."""
from datetime import date


def approved_dates(values: dict) -> dict[str, date]:
    if not values.get("start_date") or not values.get("end_date"):
        raise ValueError("Başlangıç ve bitiş tarihleri birlikte gereklidir")
    result = {key: date.fromisoformat(values[key]) for key in ("start_date", "end_date")}
    if result["end_date"] < result["start_date"]:
        raise ValueError("Bitiş tarihi başlangıçtan önce olamaz")
    return result


def selected_edition_dates(stored_end: date | None, source: dict, today: date) -> dict[str, date]:
    if stored_end is None or stored_end >= today:
        raise ValueError("Mevcut edisyon bitmeden yeni edisyona geçilemez")
    values = approved_dates(source)
    if values["start_date"] <= stored_end:
        raise ValueError("Geçerli bir sonraki edisyon seçilmelidir")
    return values
