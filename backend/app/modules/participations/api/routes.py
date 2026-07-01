from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.participations.api.dependencies import (
    get_auth_context,
    get_create_participation_use_case,
    get_delete_participation_use_case,
    get_get_participation_use_case,
    get_list_by_customer_use_case,
    get_list_by_fair_use_case,
    get_update_participation_use_case,
    require_read_permission,
)
from app.modules.participations.api.schemas import (
    CreateParticipationRequest,
    CustomerParticipationListItemResponse,
    CustomerParticipationListResponse,
    ErrorResponse,
    FairParticipantListItemResponse,
    FairParticipantListResponse,
    ParticipationResponse,
    UpdateParticipationRequest,
)
from app.modules.participations.application.commands import (
    CreateParticipationCommand,
    DeleteParticipationCommand,
    GetParticipationQuery,
    ListParticipationsByCustomerQuery,
    ListParticipantsByFairQuery,
    UpdateParticipationCommand,
)
from app.modules.participations.application.create_participation import CreateParticipationUseCase
from app.modules.participations.application.delete_participation import DeleteParticipationUseCase
from app.modules.participations.application.get_participation import GetParticipationUseCase
from app.modules.participations.application.list_by_customer import ListParticipationsByCustomerUseCase
from app.modules.participations.application.list_by_fair import ListParticipantsByFairUseCase
from app.modules.participations.application.update_participation import UpdateParticipationUseCase
from app.modules.participations.domain.exceptions import (
    ContactCustomerMismatchForParticipationError,
    ContactNotFoundForParticipationError,
    CustomerArchivedForParticipationError,
    CustomerNotFoundForParticipationError,
    DuplicateParticipationError,
    FairArchivedForParticipationError,
    FairNotFoundForParticipationError,
    InvalidParticipationStatusError,
    ParticipationAlreadyDeletedError,
    ParticipationNotFoundError,
)

router = APIRouter(prefix="/fair-participations", tags=["fair-participations"])
customer_participations_router = APIRouter(
    prefix="/customers/{customer_id}/fair-participations",
    tags=["fair-participations"],
)
fair_participants_router = APIRouter(
    prefix="/fairs/{fair_id}/participants",
    tags=["fair-participations"],
)
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _participation_response(result) -> ParticipationResponse:
    return ParticipationResponse.model_validate(result.__dict__)


@customer_participations_router.get(
    "",
    response_model=CustomerParticipationListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="List fair participations for a customer",
)
def list_participations_by_customer(
    customer_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListParticipationsByCustomerUseCase = Depends(get_list_by_customer_use_case),
) -> CustomerParticipationListResponse:
    try:
        result = use_case.execute(
            ListParticipationsByCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        )
    except CustomerNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerArchivedForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CustomerParticipationListResponse(
        items=[CustomerParticipationListItemResponse.model_validate(i.__dict__) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@fair_participants_router.get(
    "",
    response_model=FairParticipantListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="List participant companies for a fair",
)
def list_participants_by_fair(
    fair_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListParticipantsByFairUseCase = Depends(get_list_by_fair_use_case),
) -> FairParticipantListResponse:
    try:
        result = use_case.execute(
            ListParticipantsByFairQuery(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        )
    except FairNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairArchivedForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FairParticipantListResponse(
        items=[FairParticipantListItemResponse.model_validate(i.__dict__) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post(
    "",
    response_model=ParticipationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Create customer fair participation",
)
def create_participation(
    body: CreateParticipationRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateParticipationUseCase = Depends(get_create_participation_use_case),
) -> ParticipationResponse:
    try:
        result = use_case.execute(
            CreateParticipationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                **body.model_dump(),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CustomerNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerArchivedForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FairArchivedForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DuplicateParticipationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ContactNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactCustomerMismatchForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidParticipationStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _participation_response(result)


@router.get(
    "/{participation_id}",
    response_model=ParticipationResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Get participation by id",
)
def get_participation(
    participation_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetParticipationUseCase = Depends(get_get_participation_use_case),
) -> ParticipationResponse:
    try:
        result = use_case.execute(
            GetParticipationQuery(
                organization_id=auth.organization_id,
                participation_id=participation_id,
            )
        )
    except ParticipationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _participation_response(result)


@router.patch(
    "/{participation_id}",
    response_model=ParticipationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    summary="Update participation",
)
def update_participation(
    participation_id: UUID,
    body: UpdateParticipationRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateParticipationUseCase = Depends(get_update_participation_use_case),
) -> ParticipationResponse:
    data = body.model_dump(exclude_unset=True)
    set_fields = {
        key: key in data
        for key in ("hall", "stand", "notes", "primary_contact_id", "visited_at")
    }
    try:
        result = use_case.execute(
            UpdateParticipationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                participation_id=participation_id,
                hall=data.get("hall"),
                stand=data.get("stand"),
                participation_status=data.get("participation_status"),
                notes=data.get("notes"),
                primary_contact_id=data.get("primary_contact_id"),
                visited_at=data.get("visited_at"),
                is_active=data.get("is_active"),
                set_hall=set_fields["hall"],
                set_stand=set_fields["stand"],
                set_notes=set_fields["notes"],
                set_primary_contact_id=set_fields["primary_contact_id"],
                set_visited_at=set_fields["visited_at"],
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ParticipationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ParticipationAlreadyDeletedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ContactNotFoundForParticipationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactCustomerMismatchForParticipationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidParticipationStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _participation_response(result)


@router.delete(
    "/{participation_id}",
    response_model=ParticipationResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Soft delete participation",
)
def delete_participation(
    participation_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteParticipationUseCase = Depends(get_delete_participation_use_case),
) -> ParticipationResponse:
    try:
        result = use_case.execute(
            DeleteParticipationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                participation_id=participation_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ParticipationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _participation_response(result)
