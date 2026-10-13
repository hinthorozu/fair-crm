from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.super_admin import SuperAdminReader, get_super_admin_reader
from app.modules.fairs.api.dependencies import bearer_scheme, get_auth_context, get_tobb_workflow_service
from app.modules.fairs.api.dependencies import get_tobb_job_runner  # compatibility for existing dependency overrides
from app.modules.fairs.application.tobb_workflow_service import TobbWorkflowService
from app.modules.fairs.domain.exceptions import TobbReviewConflict, TobbRunNotFound

router = APIRouter(prefix="/fairs/system/tobb", tags=["fairs"])


def require_tobb_super_admin(
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    is_super_admin: SuperAdminReader = Depends(get_super_admin_reader),
) -> AuthContext:
    if credentials is None or not is_super_admin(credentials.credentials, auth.organization_id):
        raise HTTPException(403, "TOBB işlemleri Super Admin ile sınırlıdır")
    return auth


def _execute(operation):
    try:
        return operation()
    except TobbRunNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except TobbReviewConflict as exc:
        raise HTTPException(409, {"message": str(exc), "current": exc.current}) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class ReviewDecision(BaseModel):
    id: UUID
    version: int = Field(ge=1)
    decision: Literal["apply", "keep", "map", "create", "defer", "same", "different", "select"]
    target_fair_id: UUID | None = None
    source_external_id: str | None = Field(default=None, max_length=64)


class BulkDateDecision(BaseModel):
    items: list[ReviewDecision] = Field(min_length=1, max_length=100)


class SyncPreviewRequest(BaseModel):
    year: int = Field(ge=1900, le=2200)


class ChangeMappingRequest(BaseModel):
    fair_id: UUID


@router.post("/sync", status_code=202)
def start_manual_preview(body: SyncPreviewRequest, auth: AuthContext = Depends(require_tobb_super_admin),
                         service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.start_preview(body.year, user_id=auth.user_id, user_label=auth.email))


@router.get("/runs")
def list_tobb_runs(_: AuthContext = Depends(require_tobb_super_admin),
                   offset: int = Query(default=0, ge=0),
                   service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return service.history(offset=offset)


@router.get("/runs/{run_id}")
def get_tobb_run(run_id: UUID, _: AuthContext = Depends(require_tobb_super_admin),
                 service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.get_run(run_id))


@router.post("/runs/{run_id}/apply", status_code=202)
def apply_tobb_preview(run_id: UUID, _: AuthContext = Depends(require_tobb_super_admin),
                       service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.apply_preview(run_id))


@router.post("/runs/{run_id}/cancel")
def cancel_tobb_run(run_id: UUID, auth: AuthContext = Depends(require_tobb_super_admin),
                     service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.cancel(run_id, user_id=auth.user_id))


@router.post("/runs/{run_id}/retry", status_code=202)
def retry_tobb_run(run_id: UUID, auth: AuthContext = Depends(require_tobb_super_admin),
                    service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.retry(run_id, user_id=auth.user_id, user_label=auth.email))


@router.get("/reviews")
def list_reviews(search: str = Query(default="", max_length=500), kind: str | None = None,
                  _: AuthContext = Depends(require_tobb_super_admin),
                  service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return service.pending(search=search, kind=kind)


@router.post("/runs/{run_id}/retry-notification", status_code=202)
def retry_tobb_notification(run_id: UUID, _: AuthContext = Depends(require_tobb_super_admin),
                            service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.retry_notification(run_id))


@router.post("/reviews/decide")
def decide_review(body: ReviewDecision, auth: AuthContext = Depends(require_tobb_super_admin),
                   credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                   service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.decide(body.model_dump(), auth=auth, access_token=credentials.credentials))


@router.post("/reviews/dates/bulk")
def decide_date_reviews(body: BulkDateDecision, auth: AuthContext = Depends(require_tobb_super_admin),
                         credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                         service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return service.bulk_dates([item.model_dump() for item in body.items], auth=auth, access_token=credentials.credentials)


@router.get("/mappings")
def list_mappings(_: AuthContext = Depends(require_tobb_super_admin),
                   service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return service.mappings()


@router.patch("/mappings/{mapping_id}")
def change_mapping(mapping_id: UUID, body: ChangeMappingRequest, auth: AuthContext = Depends(require_tobb_super_admin),
                    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                    service: TobbWorkflowService = Depends(get_tobb_workflow_service)) -> dict:
    return _execute(lambda: service.change_mapping(mapping_id, fair_id=body.fair_id, auth=auth, access_token=credentials.credentials))
