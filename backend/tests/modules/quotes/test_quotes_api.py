from sqlalchemy import select
from uuid import UUID

from app.modules.activities.infrastructure.persistence.models import ActivityModel


def _create_quote_context(client, auth_headers):
    customer = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"display_name": "Alize Mühendislik", "status": "active"},
    )
    assert customer.status_code == 201
    fair = client.post(
        "/api/v1/fairs",
        headers=auth_headers,
        json={"name": "Franchise Expo"},
    )
    assert fair.status_code == 201
    todo = client.post(
        "/api/v1/todos",
        headers=auth_headers,
        json={
            "title": "Alize fiyat teklifi",
            "category": "teklif",
            "customer_id": customer.json()["id"],
            "source_fair_id": fair.json()["id"],
        },
    )
    assert todo.status_code == 201
    template = client.post(
        "/api/v1/quote-templates",
        headers=auth_headers,
        json={
            "name": "Fiyat Teklifi",
            "logo_url": "/uploads/logo.png",
            "source_code": (
                "<h1>{{customer_display_name}}</h1><div>{{fair_name}}</div>"
                "<time>{{quote_date}}</time><img src=\"{{logo_url}}\">"
                "{{#content_groups}}<h2>{{tag_name}}</h2><table>"
                "{{#selected_contents}}<tr><td>{{title}}</td><td>{{value}}</td></tr>"
                "{{/selected_contents}}</table>{{/content_groups}}"
            ),
        },
    )
    assert template.status_code == 201
    tag = client.post(
        "/api/v1/template-content-tags",
        headers=auth_headers,
        json={"name": "STANT İÇERİĞİ"},
    )
    assert tag.status_code == 201
    content = client.post(
        "/api/v1/template-contents",
        headers=auth_headers,
        json={"tag_id": tag.json()["id"], "title": "CAM MASA"},
    )
    assert content.status_code == 201
    return todo.json(), template.json(), content.json()


def test_quote_draft_render_and_given_activity(client, auth_headers, db_session):
    todo, template, content = _create_quote_context(client, auth_headers)
    payload = {
        "template_id": template["id"],
        "quote_date": "2026-08-09",
        "status": "draft",
        "selected_items": [{"content_id": content["id"], "value": "3 ADET"}],
    }

    created = client.post(f"/api/v1/quotes/todo/{todo['id']}", headers=auth_headers, json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    task = client.get(f"/api/v1/todos/{todo['id']}", headers=auth_headers)
    assert task.status_code == 200
    assert task.json()["status"] == "in_progress"

    rendered = client.get(f"/api/v1/quotes/todo/{todo['id']}/render", headers=auth_headers)
    assert rendered.status_code == 200
    html = rendered.json()["html"]
    assert "Alize Mühendislik" in html
    assert "Franchise Expo" in html
    assert "09.08.2026" in html
    assert "STANT İÇERİĞİ" in html
    assert "CAM MASA" in html
    assert "3 ADET" in html
    assert "{{" not in html

    payload["status"] = "given"
    updated = client.patch(f"/api/v1/quotes/todo/{todo['id']}", headers=auth_headers, json=payload)
    assert updated.status_code == 200
    assert updated.json()["status"] == "given"
    task = client.get(f"/api/v1/todos/{todo['id']}", headers=auth_headers)
    assert task.json()["status"] == "done"

    activities = db_session.scalars(
        select(ActivityModel).where(
            ActivityModel.todo_id == UUID(todo["id"]),
            ActivityModel.activity_type == "quote",
        )
    ).all()
    assert len(activities) == 2
    assert activities[-1].subject.startswith("Teklif verildi:")


def test_quote_is_organization_scoped(client, auth_headers, other_organization_id):
    todo, template, _content = _create_quote_context(client, auth_headers)
    other_headers = {**auth_headers, "X-Organization-Id": str(other_organization_id)}
    response = client.post(
        f"/api/v1/quotes/todo/{todo['id']}",
        headers=other_headers,
        json={
            "template_id": template["id"],
            "quote_date": "2026-08-09",
            "status": "draft",
            "selected_items": [],
        },
    )
    assert response.status_code == 404
