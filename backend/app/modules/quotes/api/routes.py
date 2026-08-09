import html
import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.activities.domain.entities import Activity
from app.modules.activities.infrastructure.repositories.activity_repository import SqlAlchemyActivityRepository
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel
from app.modules.quotes.api.dependencies import require_create_permission, require_delete_permission, require_read_permission, require_update_permission
from app.modules.quotes.api.schemas import QuoteRenderResponse, QuoteResponse, QuoteWriteRequest
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel
from app.modules.todos.infrastructure.persistence.models import TodoModel

router = APIRouter(prefix="/quotes", tags=["quotes"])
_LOGO_LEGACY_PREFIX = "/data/quote-template-logos/"
_LOGO_API_PREFIX = "/api/v1/data/quote-template-logos/"


def _public_logo_url(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith(_LOGO_LEGACY_PREFIX):
        return f"{_LOGO_API_PREFIX}{value[len(_LOGO_LEGACY_PREFIX):]}"
    return value


def _response(row: QuoteModel) -> QuoteResponse:
    return QuoteResponse.model_validate(row, from_attributes=True)


def _todo(db: Session, org_id: UUID, todo_id: UUID) -> TodoModel:
    row = db.scalar(select(TodoModel).where(TodoModel.id == todo_id, TodoModel.organization_id == org_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    if row.category != "teklif" or row.customer_id is None or row.source_fair_id is None:
        raise HTTPException(status_code=400, detail="Teklif görevi müşteri ve fuara bağlı olmalıdır")
    return row


def _quote(db: Session, org_id: UUID, todo_id: UUID) -> QuoteModel | None:
    return db.scalar(select(QuoteModel).where(QuoteModel.organization_id == org_id, QuoteModel.todo_id == todo_id))


def _validated_items(db: Session, org_id: UUID, body: QuoteWriteRequest) -> list[dict]:
    ids = [item.content_id for item in body.selected_items]
    rows = db.scalars(select(TemplateContentModel).where(TemplateContentModel.organization_id == org_id, TemplateContentModel.id.in_(ids))).all() if ids else []
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Geçersiz şablon içeriği seçildi")
    return [{"content_id": str(item.content_id), "value": item.value.strip()} for item in body.selected_items]


@router.get("/todo/{todo_id}", response_model=QuoteResponse | None)
def get_quote(todo_id: UUID, auth: AuthContext = Depends(require_read_permission), db: Session = Depends(get_db)):
    _todo(db, auth.organization_id, todo_id)
    row = _quote(db, auth.organization_id, todo_id)
    return _response(row) if row else None


def _prepare_write(todo_id: UUID, body: QuoteWriteRequest, auth: AuthContext, db: Session):
    todo = _todo(db, auth.organization_id, todo_id)
    template = db.scalar(select(QuoteTemplateModel).where(QuoteTemplateModel.id == body.template_id, QuoteTemplateModel.organization_id == auth.organization_id, QuoteTemplateModel.deleted_at.is_(None)))
    if template is None:
        raise HTTPException(status_code=404, detail="Teklif şablonu bulunamadı")
    items = _validated_items(db, auth.organization_id, body)
    return todo, items


@router.post("/todo/{todo_id}", response_model=QuoteResponse, status_code=201)
def create_quote(todo_id: UUID, body: QuoteWriteRequest, auth: AuthContext = Depends(require_create_permission), db: Session = Depends(get_db)):
    todo, items = _prepare_write(todo_id, body, auth, db)
    if _quote(db, auth.organization_id, todo_id) is not None:
        raise HTTPException(status_code=409, detail="Bu görev için teklif zaten mevcut")
    now = datetime.now(UTC)
    row = QuoteModel(organization_id=auth.organization_id, todo_id=todo.id, customer_id=todo.customer_id, fair_id=todo.source_fair_id, created_by=auth.user_id, created_at=now, updated_by=auth.user_id, updated_at=now, template_id=body.template_id, quote_date=body.quote_date, status=body.status, price=body.price.strip(), selected_items=items)
    db.add(row)
    todo.status = "done" if body.status == "given" else "in_progress"
    todo.completed_at = now if body.status == "given" else None
    todo.updated_at = now; todo.updated_by = auth.user_id
    activity_repo = SqlAlchemyActivityRepository(db)
    action = "Teklif verildi" if body.status == "given" else "Teklif taslağı oluşturuldu"
    activity_repo.add(Activity.create(organization_id=auth.organization_id, customer_id=todo.customer_id, todo_id=todo.id, fair_id=todo.source_fair_id, activity_type="quote", subject=f"{action}: {todo.title}", activity_date=now, status="completed", source="system", now=now))
    db.commit(); db.refresh(row)
    return _response(row)


@router.patch("/todo/{todo_id}", response_model=QuoteResponse)
def update_quote(todo_id: UUID, body: QuoteWriteRequest, auth: AuthContext = Depends(require_update_permission), db: Session = Depends(get_db)):
    todo, items = _prepare_write(todo_id, body, auth, db)
    row = _quote(db, auth.organization_id, todo_id)
    if row is None: raise HTTPException(status_code=404, detail="Teklif bulunamadı")
    previous_status = row.status
    now = datetime.now(UTC)
    row.template_id = body.template_id; row.quote_date = body.quote_date; row.status = body.status; row.price = body.price.strip(); row.selected_items = items; row.updated_by = auth.user_id; row.updated_at = now
    todo.status = "done" if body.status == "given" else "in_progress"
    todo.completed_at = now if body.status == "given" else None
    todo.updated_at = now; todo.updated_by = auth.user_id
    if previous_status != "given" and body.status == "given":
        SqlAlchemyActivityRepository(db).add(Activity.create(organization_id=auth.organization_id, customer_id=todo.customer_id, todo_id=todo.id, fair_id=todo.source_fair_id, activity_type="quote", subject=f"Teklif verildi: {todo.title}", activity_date=now, status="completed", source="system", now=now))
    db.commit(); db.refresh(row)
    return _response(row)


def _render(row: QuoteModel, db: Session) -> str:
    customer = db.get(CustomerModel, row.customer_id); fair = db.get(FairModel, row.fair_id)
    template = db.get(QuoteTemplateModel, row.template_id); version = db.get(QuoteTemplateVersionModel, template.current_version_id)
    content_ids = [UUID(item["content_id"]) for item in row.selected_items]
    contents = db.scalars(select(TemplateContentModel).where(TemplateContentModel.id.in_(content_ids))).all() if content_ids else []
    tags = {tag.id: tag for tag in db.scalars(select(TemplateContentTagModel).where(TemplateContentTagModel.organization_id == row.organization_id)).all()}
    values = {UUID(item["content_id"]): item["value"] for item in row.selected_items}
    groups: dict[UUID, list[TemplateContentModel]] = {}
    for item in contents: groups.setdefault(item.tag_id, []).append(item)
    source = version.source_code
    block_pattern = re.compile(r"{{#content_groups}}(.*?){{/content_groups}}", re.S)
    inner_match = block_pattern.search(source)
    if inner_match:
        group_template = inner_match.group(1)
        rendered_groups = []
        item_pattern = re.compile(r"{{#selected_contents}}(.*?){{/selected_contents}}", re.S)
        for tag_id, group_items in groups.items():
            item_match = item_pattern.search(group_template)
            rendered_items = ""
            if item_match:
                rendered_items = "".join(item_match.group(1).replace("{{title}}", html.escape(item.title)).replace("{{value}}", html.escape(values[item.id])) for item in group_items)
            group_html = item_pattern.sub(rendered_items, group_template).replace("{{tag_name}}", html.escape(tags[tag_id].name))
            rendered_groups.append(group_html)
        source = block_pattern.sub("".join(rendered_groups), source)
    replacements = {"{{logo_url}}": _public_logo_url(version.logo_url), "{{customer_display_name}}": customer.display_name, "{{fair_name}}": fair.name, "{{quote_date}}": row.quote_date.strftime("%d.%m.%Y"), "{fiyat}": row.price or ""}
    for key, value in replacements.items(): source = source.replace(key, html.escape(value, quote=True))
    return source


@router.get("/todo/{todo_id}/render", response_model=QuoteRenderResponse)
def render_quote(todo_id: UUID, auth: AuthContext = Depends(require_read_permission), db: Session = Depends(get_db)):
    row = _quote(db, auth.organization_id, todo_id)
    if row is None: raise HTTPException(status_code=404, detail="Teklif henüz kaydedilmedi")
    return QuoteRenderResponse(html=_render(row, db))


@router.delete("/todo/{todo_id}", status_code=204)
def delete_quote(todo_id: UUID, auth: AuthContext = Depends(require_delete_permission), db: Session = Depends(get_db)):
    row = _quote(db, auth.organization_id, todo_id)
    if row is None: raise HTTPException(status_code=404, detail="Teklif bulunamadı")
    db.delete(row); db.commit()
