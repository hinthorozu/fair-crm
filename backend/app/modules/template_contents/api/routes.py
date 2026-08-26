from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter
from app.modules.mail_templates.api.dependencies import bearer_scheme, get_audit_adapter
from app.modules.template_contents.api.dependencies import require_create_permission, require_delete_permission, require_read_permission, require_update_permission
from app.modules.template_contents.api.schemas import (
    ContentCreateRequest, ContentListResponse, ContentResponse,
    TagCreateRequest, TagListResponse, TagResponse,
)
from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel

router = APIRouter(tags=["template-contents"])


def _token(credentials: HTTPAuthorizationCredentials | None) -> str:
    return credentials.credentials if credentials else "dev-bypass"


def _tag(db: Session, organization_id, tag_id):
    row = db.scalars(select(TemplateContentTagModel).where(TemplateContentTagModel.id == tag_id, TemplateContentTagModel.organization_id == organization_id)).first()
    if row is None: raise HTTPException(status_code=404, detail="İçerik etiketi bulunamadı.")
    return row


def _content(db: Session, organization_id, content_id):
    row = db.scalars(select(TemplateContentModel).where(TemplateContentModel.id == content_id, TemplateContentModel.organization_id == organization_id)).first()
    if row is None: raise HTTPException(status_code=404, detail="İçerik bulunamadı.")
    return row


@router.get("/template-content-tags", response_model=TagListResponse)
def list_tags(auth: AuthContext = Depends(require_read_permission), db: Session = Depends(get_db)):
    rows = db.scalars(select(TemplateContentTagModel).where(TemplateContentTagModel.organization_id == auth.organization_id).order_by(TemplateContentTagModel.name)).all()
    return TagListResponse(items=[TagResponse(id=row.id, name=row.name, created_at=row.created_at) for row in rows])


@router.post("/template-content-tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    body: TagCreateRequest, auth: AuthContext = Depends(require_create_permission),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    row = TemplateContentTagModel(organization_id=auth.organization_id, name=body.name.strip(), created_at=now, updated_at=now)
    db.add(row)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Bu içerik etiketi zaten mevcut.")
    db.refresh(row)
    audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content_tag.created", resource_type="template_content_tag", resource_id=str(row.id), new_values={"name": row.name})
    return TagResponse(id=row.id, name=row.name, created_at=row.created_at)


@router.patch("/template-content-tags/{tag_id}", response_model=TagResponse)
def update_tag(tag_id: UUID, body: TagCreateRequest, auth: AuthContext = Depends(require_update_permission), credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db)):
    row = _tag(db, auth.organization_id, tag_id); old_name = row.name; row.name = body.name.strip(); row.updated_at = datetime.now(timezone.utc)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Bu içerik etiketi zaten mevcut.")
    audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content_tag.updated", resource_type="template_content_tag", resource_id=str(row.id), old_values={"name": old_name}, new_values={"name": row.name})
    return TagResponse(id=row.id, name=row.name, created_at=row.created_at)


@router.delete("/template-content-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: UUID, auth: AuthContext = Depends(require_delete_permission), credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db)):
    row = _tag(db, auth.organization_id, tag_id)
    if db.scalars(select(TemplateContentModel).where(TemplateContentModel.tag_id == row.id).limit(1)).first() is not None: raise HTTPException(status_code=409, detail="Bu etikete bağlı içerikler olduğu için silinemez.")
    resource_id = str(row.id); db.delete(row); db.commit(); audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content_tag.deleted", resource_type="template_content_tag", resource_id=resource_id)


@router.get("/template-contents", response_model=ContentListResponse)
def list_contents(auth: AuthContext = Depends(require_read_permission), db: Session = Depends(get_db)):
    rows = db.execute(
        select(TemplateContentModel, TemplateContentTagModel.name)
        .join(TemplateContentTagModel, TemplateContentTagModel.id == TemplateContentModel.tag_id)
        .where(
            TemplateContentModel.organization_id == auth.organization_id,
            TemplateContentTagModel.organization_id == auth.organization_id,
        )
        .order_by(TemplateContentModel.title)
    ).all()
    return ContentListResponse(items=[
        ContentResponse(id=row.id, tag_id=row.tag_id, tag_name=tag_name, title=row.title, created_at=row.created_at)
        for row, tag_name in rows
    ])


@router.post("/template-contents", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def create_content(
    body: ContentCreateRequest, auth: AuthContext = Depends(require_create_permission),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db),
):
    tag = db.scalars(select(TemplateContentTagModel).where(TemplateContentTagModel.id == body.tag_id, TemplateContentTagModel.organization_id == auth.organization_id)).first()
    if tag is None: raise HTTPException(status_code=404, detail="İçerik etiketi bulunamadı.")
    now = datetime.now(timezone.utc)
    row = TemplateContentModel(organization_id=auth.organization_id, tag_id=tag.id, title=body.title.strip(), created_at=now, updated_at=now)
    db.add(row); db.commit(); db.refresh(row)
    audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content.created", resource_type="template_content", resource_id=str(row.id), new_values={"title": row.title, "tag_id": str(tag.id)})
    return ContentResponse(id=row.id, tag_id=tag.id, tag_name=tag.name, title=row.title, created_at=row.created_at)


@router.patch("/template-contents/{content_id}", response_model=ContentResponse)
def update_content(content_id: UUID, body: ContentCreateRequest, auth: AuthContext = Depends(require_update_permission), credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db)):
    row = _content(db, auth.organization_id, content_id); tag = _tag(db, auth.organization_id, body.tag_id)
    old = {"title": row.title, "tag_id": str(row.tag_id)}; row.title = body.title.strip(); row.tag_id = tag.id; row.updated_at = datetime.now(timezone.utc); db.commit()
    audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content.updated", resource_type="template_content", resource_id=str(row.id), old_values=old, new_values={"title": row.title, "tag_id": str(tag.id)})
    return ContentResponse(id=row.id, tag_id=tag.id, tag_name=tag.name, title=row.title, created_at=row.created_at)


@router.delete("/template-contents/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(content_id: UUID, auth: AuthContext = Depends(require_delete_permission), credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter), db: Session = Depends(get_db)):
    row = _content(db, auth.organization_id, content_id); resource_id = str(row.id); db.delete(row); db.commit(); audit.record_event(organization_id=auth.organization_id, access_token=_token(credentials), action="template_content.deleted", resource_type="template_content", resource_id=resource_id)
