"""Live verification for customer fair participation API."""

import os
import sys
from uuid import uuid4

import httpx

BASE = os.environ.get("FAIR_CRM_API_BASE", "http://127.0.0.1:8001")
ORG = os.environ.get("FAIR_CRM_ORG_ID", "")
TOKEN = os.environ.get("FAIR_CRM_TOKEN", "dev-bypass")


def headers(org_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json",
    }


def main() -> int:
    org_id = ORG or str(uuid4())
    h = headers(org_id)
    client = httpx.Client(base_url=BASE, timeout=30.0)

    print(f"Health: {client.get('/health').status_code}")
    print(f"OpenAPI paths with fair-participations: ", end="")
    spec = client.get("/openapi.json").json()
    paths = [p for p in spec.get("paths", {}) if "fair-participation" in p or "participants" in p]
    print(len(paths), "endpoints")

    customer = client.post(
        "/api/v1/customers",
        headers=h,
        json={"display_name": f"Live Part Co {uuid4().hex[:6]}", "status": "active"},
    )
    customer.raise_for_status()
    customer_id = customer.json()["id"]

    fair = client.post(
        "/api/v1/fairs",
        headers=h,
        json={"name": f"Live Fair {uuid4().hex[:6]}", "status": "planned"},
    )
    fair.raise_for_status()
    fair_id = fair.json()["id"]

    create = client.post(
        "/api/v1/fair-participations",
        headers=h,
        json={
            "customer_id": customer_id,
            "fair_id": fair_id,
            "hall": "A1",
            "stand": "42",
            "participation_status": "exhibitor",
        },
    )
    create.raise_for_status()
    participation_id = create.json()["id"]
    print(f"Created participation: {participation_id}")

    dup = client.post(
        "/api/v1/fair-participations",
        headers=h,
        json={"customer_id": customer_id, "fair_id": fair_id},
    )
    assert dup.status_code == 409, dup.text
    print("Duplicate protection: OK")

    by_customer = client.get(f"/api/v1/customers/{customer_id}/fair-participations", headers=h)
    by_customer.raise_for_status()
    assert by_customer.json()["total"] == 1
    print("List by customer: OK")

    by_fair = client.get(f"/api/v1/fairs/{fair_id}/participants", headers=h)
    by_fair.raise_for_status()
    assert by_fair.json()["total"] == 1
    print("List by fair: OK")

    client.delete(f"/api/v1/fair-participations/{participation_id}", headers=h).raise_for_status()
    print("Delete: OK")

    print("PASS — participations live verification")
    return 0


if __name__ == "__main__":
    sys.exit(main())
