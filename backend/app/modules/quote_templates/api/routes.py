from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter
from app.modules.mail_templates.api.dependencies import bearer_scheme, get_audit_adapter
from app.modules.quote_templates.api.dependencies import (
    require_create_permission,
    require_logo_upload_permission,
    require_read_permission,
    require_update_permission,
)
from app.modules.quote_templates.api.schemas import (
    LogoUploadResponse,
    QuoteTemplateListResponse,
    QuoteTemplateResponse,
    QuoteTemplateWriteRequest,
)
from app.modules.quote_templates.infrastructure.logo_storage import (
    LOGO_API_PREFIX,
    LOGO_MEDIA_TYPES,
    LOGO_STORAGE_ROOT,
    normalize_logo_url,
    resolve_logo_file,
    validate_logo_url_ownership,
)
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel

router = APIRouter(prefix="/quote-templates", tags=["quote-templates"])
asset_router = APIRouter(prefix="/data/quote-template-logos", tags=["quote-template-logos"])
_ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}


def _response(template: QuoteTemplateModel, version: QuoteTemplateVersionModel) -> QuoteTemplateResponse:
    return QuoteTemplateResponse(
        id=template.id,
        organization_id=template.organization_id,
        name=template.name,
        current_version_id=version.id,
        version_number=version.version_number,
        logo_url=normalize_logo_url(version.logo_url),
        source_code=version.source_code,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _find(db: Session, organization_id: UUID, template_id: UUID) -> QuoteTemplateModel:
    item = db.scalars(
        select(QuoteTemplateModel).where(
            QuoteTemplateModel.id == template_id,
            QuoteTemplateModel.organization_id == organization_id,
            QuoteTemplateModel.deleted_at.is_(None),
        )
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Teklif şablonu bulunamadı.")
    return item


def _owned_logo_url(value: str | None, organization_id: UUID) -> str | None:
    try:
        return validate_logo_url_ownership(value, organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Logo bu organizasyona ait değil.") from exc


@asset_router.get("/{asset_organization_id}/{filename}")
def get_quote_template_logo(
    asset_organization_id: UUID,
    filename: str,
    auth: AuthContext = Depends(require_read_permission),
):
    if asset_organization_id != auth.organization_id:
        raise HTTPException(status_code=404, detail="Logo bulunamadı.")
    path = resolve_logo_file(asset_organization_id, filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Logo bulunamadı.")
    media_type = LOGO_MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise HTTPException(status_code=404, detail="Logo bulunamadı.")
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("", response_model=QuoteTemplateListResponse)
def list_quote_templates(
    auth: AuthContext = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    templates = db.scalars(
        select(QuoteTemplateModel)
        .where(
            QuoteTemplateModel.organization_id == auth.organization_id,
            QuoteTemplateModel.deleted_at.is_(None),
        )
        .order_by(QuoteTemplateModel.name)
    ).all()
    items = []
    for template in templates:
        version = db.scalar(
            select(QuoteTemplateVersionModel).where(
                QuoteTemplateVersionModel.id == template.current_version_id,
                QuoteTemplateVersionModel.template_id == template.id,
            )
        )
        if version is not None:
            items.append(_response(template, version))
    return QuoteTemplateListResponse(items=items)


@router.post("", response_model=QuoteTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_quote_template(
    body: QuoteTemplateWriteRequest,
    auth: AuthContext = Depends(require_create_permission),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    template = QuoteTemplateModel(
        organization_id=auth.organization_id,
        name=body.name.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(template)
    db.flush()
    version = QuoteTemplateVersionModel(
        template_id=template.id,
        version_number=1,
        logo_url=_owned_logo_url(body.logo_url, auth.organization_id),
        source_code=body.source_code,
        created_at=now,
        created_by=auth.user_id,
    )
    db.add(version)
    db.flush()
    template.current_version_id = version.id
    db.commit()
    db.refresh(template)
    response = _response(template, version)
    audit.record_event(
        organization_id=auth.organization_id,
        access_token=credentials.credentials if credentials else "dev-bypass",
        action="quote_template.created",
        resource_type="quote_template",
        resource_id=str(template.id),
        new_values={"name": template.name, "version_number": 1},
    )
    return response


@router.patch("/{template_id}", response_model=QuoteTemplateResponse)
def update_quote_template(
    template_id: UUID,
    body: QuoteTemplateWriteRequest,
    auth: AuthContext = Depends(require_update_permission),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
    db: Session = Depends(get_db),
):
    template = _find(db, auth.organization_id, template_id)
    old_values = {"name": template.name, "current_version_id": str(template.current_version_id)}
    now = datetime.now(timezone.utc)
    next_number = (
        db.scalar(
            select(func.max(QuoteTemplateVersionModel.version_number)).where(
                QuoteTemplateVersionModel.template_id == template.id
            )
        )
        or 0
    ) + 1
    version = QuoteTemplateVersionModel(
        template_id=template.id,
        version_number=next_number,
        logo_url=_owned_logo_url(body.logo_url, auth.organization_id),
        source_code=body.source_code,
        created_at=now,
        created_by=auth.user_id,
    )
    db.add(version)
    db.flush()
    template.name = body.name.strip()
    template.current_version_id = version.id
    template.updated_at = now
    db.commit()
    db.refresh(template)
    response = _response(template, version)
    audit.record_event(
        organization_id=auth.organization_id,
        access_token=credentials.credentials if credentials else "dev-bypass",
        action="quote_template.updated",
        resource_type="quote_template",
        resource_id=str(template.id),
        old_values=old_values,
        new_values={"name": template.name, "version_number": next_number},
    )
    return response


@router.post("/logo", response_model=LogoUploadResponse)
async def upload_quote_logo(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_logo_upload_permission),
):
    extension = _ALLOWED_LOGO_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=400, detail="Logo PNG, JPG, SVG veya WebP olmalıdır.")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo en fazla 5 MB olabilir.")
    organization_dir = LOGO_STORAGE_ROOT / str(auth.organization_id)
    organization_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (organization_dir / filename).write_bytes(content)
    return LogoUploadResponse(url=f"{LOGO_API_PREFIX}{auth.organization_id}/{filename}")