from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.ports import AuditPort
from app.modules.cost_catalog.api.dependencies import (
    CATEGORY_CREATE,
    CATEGORY_DELETE,
    CATEGORY_UPDATE,
    CATEGORY_VIEW,
    PRODUCT_CREATE,
    PRODUCT_DELETE,
    PRODUCT_UPDATE,
    PRODUCT_VIEW,
    require_permission,
)
from app.modules.cost_catalog.api.schemas import (
    CostCategoryListResponse,
    CostCategoryOptionResponse,
    CostCategoryOptionsResponse,
    CostCategoryResponse,
    CostCategoryWriteRequest,
    CostProductListResponse,
    CostProductResponse,
    CostProductWriteRequest,
)
from app.modules.cost_catalog.infrastructure.models import CostCategoryModel, CostProductModel
from app.modules.cost_catalog.slug import next_available_slug, slugify
from app.modules.mail_templates.api.dependencies import bearer_scheme, get_audit_adapter

router = APIRouter(prefix="/cost-catalog", tags=["cost-catalog"])


def _category_response(item: CostCategoryModel) -> CostCategoryResponse:
    return CostCategoryResponse(
        id=item.id,
        organization_id=item.organization_id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _product_response(item: CostProductModel, category_name: str) -> CostProductResponse:
    return CostProductResponse(
        id=item.id,
        organization_id=item.organization_id,
        category_id=item.category_id,
        category_name=category_name,
        name=item.name,
        slug=item.slug,
        unit=item.unit,
        unit_price=item.unit_price,
        currency=item.currency,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _find_category(db: Session, organization_id: UUID, category_id: UUID) -> CostCategoryModel:
    item = db.scalar(
        select(CostCategoryModel).where(
            CostCategoryModel.id == category_id,
            CostCategoryModel.organization_id == organization_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return item


def _find_product(db: Session, organization_id: UUID, product_id: UUID) -> CostProductModel:
    item = db.scalar(
        select(CostProductModel).where(
            CostProductModel.id == product_id,
            CostProductModel.organization_id == organization_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return item


def _unique_category_slug(
    db: Session,
    organization_id: UUID,
    requested_slug: str,
    *,
    exclude_category_id: UUID | None = None,
) -> str:
    stmt = select(CostCategoryModel.slug).where(CostCategoryModel.organization_id == organization_id)
    if exclude_category_id is not None:
        stmt = stmt.where(CostCategoryModel.id != exclude_category_id)
    existing_slugs = set(db.scalars(stmt).all())
    return next_available_slug(slugify(requested_slug), existing_slugs)


def _token(credentials: HTTPAuthorizationCredentials | None) -> str:
    return credentials.credentials if credentials and credentials.credentials else "dev-bypass"


def _audit(
    audit: AuditPort,
    credentials: HTTPAuthorizationCredentials | None,
    auth: AuthContext,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    audit.record_event(
        organization_id=auth.organization_id,
        access_token=_token(credentials),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        old_values=old_values,
        new_values=new_values,
    )


@router.get("/categories", response_model=CostCategoryListResponse)
def list_categories(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(CATEGORY_VIEW)),
) -> CostCategoryListResponse:
    items = db.scalars(
        select(CostCategoryModel)
        .where(CostCategoryModel.organization_id == auth.organization_id)
        .order_by(CostCategoryModel.name)
    ).all()
    return CostCategoryListResponse(items=[_category_response(item) for item in items])


@router.post("/categories", response_model=CostCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CostCategoryWriteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(CATEGORY_CREATE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CostCategoryResponse:
    name = payload.name.strip()
    requested_slug = payload.slug.strip() or name
    description = payload.description.strip() if payload.description else None

    for _ in range(20):
        now = datetime.now(timezone.utc)
        item = CostCategoryModel(
            organization_id=auth.organization_id,
            name=name,
            slug=_unique_category_slug(db, auth.organization_id, requested_slug),
            description=description,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue

        db.refresh(item)
        result = _category_response(item)
        _audit(
            audit,
            credentials,
            auth,
            action="create",
            resource_type="cost_catalog.category",
            resource_id=item.id,
            new_values=result.model_dump(mode="json"),
        )
        return result

    raise HTTPException(status_code=409, detail="Unique category slug could not be generated")


@router.patch("/categories/{category_id}", response_model=CostCategoryResponse)
def update_category(
    category_id: UUID,
    payload: CostCategoryWriteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(CATEGORY_UPDATE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CostCategoryResponse:
    item = _find_category(db, auth.organization_id, category_id)
    old = _category_response(item).model_dump(mode="json")
    name = payload.name.strip()
    requested_slug = payload.slug.strip() or name
    description = payload.description.strip() if payload.description else None

    for _ in range(20):
        item = _find_category(db, auth.organization_id, category_id)
        item.name = name
        item.slug = _unique_category_slug(
            db,
            auth.organization_id,
            requested_slug,
            exclude_category_id=item.id,
        )
        item.description = description
        item.updated_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue

        db.refresh(item)
        result = _category_response(item)
        _audit(
            audit,
            credentials,
            auth,
            action="update",
            resource_type="cost_catalog.category",
            resource_id=item.id,
            old_values=old,
            new_values=result.model_dump(mode="json"),
        )
        return result

    raise HTTPException(status_code=409, detail="Unique category slug could not be generated")


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(CATEGORY_DELETE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Response:
    item = _find_category(db, auth.organization_id, category_id)
    product = db.scalar(
        select(CostProductModel.id).where(
            CostProductModel.organization_id == auth.organization_id,
            CostProductModel.category_id == item.id,
        ).limit(1)
    )
    if product is not None:
        raise HTTPException(status_code=409, detail="Bu kategoride ürünler bulunduğu için kategori silinemez.")
    old = _category_response(item).model_dump(mode="json")
    db.delete(item)
    db.commit()
    _audit(audit, credentials, auth, action="delete", resource_type="cost_catalog.category", resource_id=category_id, old_values=old)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/products/category-options", response_model=CostCategoryOptionsResponse)
def list_product_category_options(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(PRODUCT_VIEW)),
) -> CostCategoryOptionsResponse:
    items = db.scalars(
        select(CostCategoryModel)
        .where(CostCategoryModel.organization_id == auth.organization_id)
        .order_by(CostCategoryModel.name)
    ).all()
    return CostCategoryOptionsResponse(items=[CostCategoryOptionResponse(id=item.id, name=item.name) for item in items])


@router.get("/products", response_model=CostProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(PRODUCT_VIEW)),
) -> CostProductListResponse:
    rows = db.execute(
        select(CostProductModel, CostCategoryModel.name)
        .join(CostCategoryModel, CostCategoryModel.id == CostProductModel.category_id)
        .where(
            CostProductModel.organization_id == auth.organization_id,
            CostCategoryModel.organization_id == auth.organization_id,
        )
        .order_by(CostProductModel.name)
    ).all()
    return CostProductListResponse(items=[_product_response(product, category_name) for product, category_name in rows])


@router.post("/products", response_model=CostProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: CostProductWriteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(PRODUCT_CREATE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CostProductResponse:
    category = _find_category(db, auth.organization_id, payload.category_id)
    now = datetime.now(timezone.utc)
    item = CostProductModel(
        organization_id=auth.organization_id,
        category_id=category.id,
        name=payload.name.strip(),
        slug=payload.slug.strip(),
        unit=payload.unit,
        unit_price=payload.unit_price,
        currency=payload.currency,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product slug already exists")
    db.refresh(item)
    result = _product_response(item, category.name)
    _audit(audit, credentials, auth, action="create", resource_type="cost_catalog.product", resource_id=item.id, new_values=result.model_dump(mode="json"))
    return result


@router.patch("/products/{product_id}", response_model=CostProductResponse)
def update_product(
    product_id: UUID,
    payload: CostProductWriteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(PRODUCT_UPDATE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CostProductResponse:
    item = _find_product(db, auth.organization_id, product_id)
    category = _find_category(db, auth.organization_id, payload.category_id)
    old = _product_response(item, item.category.name).model_dump(mode="json")
    item.category_id = category.id
    item.name = payload.name.strip()
    item.slug = payload.slug.strip()
    item.unit = payload.unit
    item.unit_price = payload.unit_price
    item.currency = payload.currency
    item.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product slug already exists")
    db.refresh(item)
    result = _product_response(item, category.name)
    _audit(audit, credentials, auth, action="update", resource_type="cost_catalog.product", resource_id=item.id, old_values=old, new_values=result.model_dump(mode="json"))
    return result


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_permission(PRODUCT_DELETE)),
    audit: AuditPort = Depends(get_audit_adapter),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Response:
    item = _find_product(db, auth.organization_id, product_id)
    old = _product_response(item, item.category.name).model_dump(mode="json")
    db.delete(item)
    db.commit()
    _audit(audit, credentials, auth, action="delete", resource_type="cost_catalog.product", resource_id=product_id, old_values=old)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
