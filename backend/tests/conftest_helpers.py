"""Shared helpers for standard list API response assertions."""


def list_body(json: dict) -> dict:
    """Return list payload; accepts raw response dict from TestClient."""
    return json


def pagination_from(json: dict) -> dict:
    """Extract pagination block from standard or legacy list responses."""
    if "pagination" in json:
        return json["pagination"]
    return {
        "page": json.get("page", 1),
        "pageSize": json.get("page_size", json.get("pageSize", 25)),
        "totalItems": json.get("total", json.get("totalItems", 0)),
        "totalPages": json.get("total_pages", json.get("totalPages", 0)),
    }
