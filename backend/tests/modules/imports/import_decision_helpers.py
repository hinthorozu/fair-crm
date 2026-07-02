"""Shared helpers for import decision apply tests."""


def apply_import_decisions(client, auth_headers, batch_id: str, **payload):
    return client.post(
        f"/api/v1/imports/{batch_id}/decisions/apply",
        headers=auth_headers,
        json=payload,
    )


def set_decision_and_apply(client, auth_headers, batch_id: str, row_id: str, decision_payload: dict):
    decision = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}/decision",
        headers=auth_headers,
        json=decision_payload,
    )
    assert decision.status_code == 200
    applied = apply_import_decisions(client, auth_headers, batch_id, row_ids=[row_id])
    assert applied.status_code == 200
    return applied
