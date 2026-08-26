from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel


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


def _create_draft_quote(client, auth_headers):
    todo, template, content = _create_quote_context(client, auth_headers)
    payload = {
        "template_id": template["id"],
        "quote_date": "2026-08-09",
        "status": "draft",
        "selected_items": [{"content_id": content["id"], "value": "3 ADET"}],
    }
    created = client.post(f"/api/v1/quotes/todo/{todo['id']}", headers=auth_headers, json=payload)
    assert created.status_code == 201
    return todo, template, content, payload


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


def test_quote_render_fails_closed_for_cross_tenant_derived_ids(
    client,
    auth_headers,
    db_session,
    organization_id,
    other_organization_id,
):
    todo, template, content, _payload = _create_draft_quote(client, auth_headers)
    quote = db_session.scalar(select(QuoteModel).where(QuoteModel.todo_id == UUID(todo["id"])))
    assert quote is not None

    now = datetime.now(tz=UTC)
    foreign_customer = CustomerModel(
        id=uuid4(),
        organization_id=other_organization_id,
        display_name="FOREIGN CUSTOMER",
        normalized_name="foreign customer",
        customer_type="lead",
        status="active",
        source="manual",
        created_at=now,
        updated_at=now,
    )
    foreign_fair = FairModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="FOREIGN FAIR",
        status="planned",
        normalized_name="foreign fair",
        created_at=now,
        updated_at=now,
    )
    foreign_template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="FOREIGN TEMPLATE",
        created_at=now,
        updated_at=now,
    )
    foreign_tag = TemplateContentTagModel(
        id=uuid4(),
        organization_id=other_organization_id,
        name="FOREIGN TAG",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([foreign_customer, foreign_fair, foreign_template, foreign_tag])
    db_session.flush()

    foreign_version = QuoteTemplateVersionModel(
        id=uuid4(),
        template_id=foreign_template.id,
        version_number=1,
        source_code="<h1>FOREIGN TEMPLATE SOURCE</h1>",
        created_at=now,
    )
    foreign_content = TemplateContentModel(
        id=uuid4(),
        organization_id=other_organization_id,
        tag_id=foreign_tag.id,
        title="FOREIGN CONTENT",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([foreign_version, foreign_content])
    db_session.flush()
    foreign_template.current_version_id = foreign_version.id
    db_session.flush()

    owner_customer_id = quote.customer_id
    owner_fair_id = quote.fair_id
    owner_template_id = quote.template_id
    owner_selected_items = list(quote.selected_items)
    owner_template = db_session.get(QuoteTemplateModel, UUID(template["id"]))
    owner_content = db_session.get(TemplateContentModel, UUID(content["id"]))
    assert owner_template is not None and owner_content is not None
    owner_version_id = owner_template.current_version_id
    owner_tag_id = owner_content.tag_id

    def assert_render_rejected() -> None:
        db_session.flush()
        response = client.get(
            f"/api/v1/quotes/todo/{todo['id']}/render",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Teklif render verisi bulunamadı"
        assert "FOREIGN" not in response.text

    quote.customer_id = foreign_customer.id
    assert_render_rejected()
    quote.customer_id = owner_customer_id

    quote.fair_id = foreign_fair.id
    assert_render_rejected()
    quote.fair_id = owner_fair_id

    quote.template_id = foreign_template.id
    assert_render_rejected()
    quote.template_id = owner_template_id

    quote.selected_items = [{"content_id": str(foreign_content.id), "value": "FOREIGN VALUE"}]
    assert_render_rejected()
    quote.selected_items = owner_selected_items

    owner_template.current_version_id = foreign_version.id
    assert_render_rejected()
    owner_template.current_version_id = owner_version_id

    owner_content.tag_id = foreign_tag.id
    assert_render_rejected()
    owner_content.tag_id = owner_tag_id

    db_session.flush()
    rendered = client.get(
        f"/api/v1/quotes/todo/{todo['id']}/render",
        headers=auth_headers,
    )
    assert rendered.status_code == 200
    assert "Alize Mühendislik" in rendered.json()["html"]
    assert quote.organization_id == organization_id
