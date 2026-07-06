from tests.conftest_helpers import pagination_from
from tests.modules.todos.test_todo_worklist_api import WORKLIST_BASE, _seed_worklist_scenario


def test_record_worklist_activity_updates_state_and_progress(
    client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    outcome_id = str(scenario["outcome"].id)

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/activities",
        headers=auth_headers,
        json={
            "outcome_id": outcome_id,
            "note": "Müşteri teklif istedi, takipte kalacak.",
            "action_required": True,
            "data_problem": False,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["worklist_row"]["primary_status"] == "in_follow_up"
    assert body["worklist_row"]["last_note_summary"] == "Müşteri teklif istedi, takipte kalacak."
    assert body["worklist_row"]["action_required"] is True
    assert body["progress"]["not_started"] == 0
    assert body["progress"]["in_follow_up"] == 2

    yapilmadi = client.get(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}?filter=yapilmadi",
        headers=auth_headers,
    )
    assert yapilmadi.status_code == 200
    assert pagination_from(yapilmadi.json())["totalItems"] == 0

    takipte = client.get(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}?filter=takipte",
        headers=auth_headers,
    )
    names = {item["customer_name"] for item in takipte.json()["items"]}
    assert "Alpha Corp" in names


def test_record_worklist_activity_advance_to_next(
    client, auth_headers, db_session, organization_id, user_id
):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    outcome_id = str(scenario["outcome"].id)

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/activities",
        headers=auth_headers,
        json={
            "outcome_id": outcome_id,
            "note": "İlk müşteri tamamlandı.",
            "advance_to_next": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["next_customer_id"] is None


def test_worklist_modal_context(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)

    response = client.get(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/modal",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["customer_name"] == "Alpha Corp"
    assert body["todo_title"] == "Fair worklist"
    assert len(body["outcomes"]) >= 1
    assert body["worklist_row"]["primary_status"] == "not_started"


def test_record_worklist_activity_requires_note(client, auth_headers, db_session, organization_id, user_id):
    scenario = _seed_worklist_scenario(db_session, organization_id, user_id)
    todo_id = scenario["todo_id"]
    customer_id = str(scenario["customers"]["alpha"].id)
    outcome_id = str(scenario["outcome"].id)

    response = client.post(
        f"{WORKLIST_BASE.format(todo_id=todo_id)}/customers/{customer_id}/activities",
        headers=auth_headers,
        json={"outcome_id": outcome_id, "note": "   "},
    )
    assert response.status_code == 400
