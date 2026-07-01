from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.contacts.api.dependencies import (
    get_auth_context,
    get_create_contact_use_case,
    get_delete_contact_use_case,
    get_get_contact_use_case,
    get_list_contacts_by_customer_use_case,
    get_update_contact_use_case,
    require_read_permission,
)
from app.modules.contacts.api.schemas import (
    ContactListResponse,
    ContactResponse,
    CreateContactRequest,
    ErrorResponse,
    UpdateContactRequest,
)
from app.modules.contacts.application.commands import (
    CreateContactCommand,
    DeleteContactCommand,
    GetContactQuery,
    ListContactsByCustomerQuery,
    UpdateContactCommand,
)
from app.modules.contacts.application.create_contact import CreateContactUseCase
from app.modules.contacts.application.delete_contact import DeleteContactUseCase
from app.modules.contacts.application.get_contact import GetContactUseCase
from app.modules.contacts.application.list_contacts_by_customer import ListContactsByCustomerUseCase
from app.modules.contacts.application.update_contact import UpdateContactUseCase
from app.modules.contacts.domain.exceptions import (
    ContactAlreadyDeletedError,
    ContactNotFoundError,
    CustomerArchivedForContactError,
    CustomerNotFoundForContactError,
    InvalidContactEmailError,
    InvalidContactNameError,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])
customer_contacts_router = APIRouter(prefix="/customers/{customer_id}/contacts", tags=["contacts"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> ContactResponse:
    return ContactResponse.model_validate(result.__dict__)


@customer_contacts_router.get(
    "",
    response_model=ContactListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_contacts_by_customer(
    customer_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListContactsByCustomerUseCase = Depends(get_list_contacts_by_customer_use_case),
) -> ContactListResponse:
    try:
        result = use_case.execute(
            ListContactsByCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        )
    except CustomerNotFoundForContactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ContactListResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def create_contact(
    body: CreateContactRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateContactUseCase = Depends(get_create_contact_use_case),
) -> ContactResponse:
    try:
        result = use_case.execute(
            CreateContactCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CustomerNotFoundForContactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerArchivedForContactError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContactNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContactEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_contact(
    contact_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetContactUseCase = Depends(get_get_contact_use_case),
) -> ContactResponse:
    try:
        result = use_case.execute(
            GetContactQuery(
                organization_id=auth.organization_id,
                contact_id=contact_id,
            )
        )
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_contact(
    contact_id: UUID,
    body: UpdateContactRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateContactUseCase = Depends(get_update_contact_use_case),
) -> ContactResponse:
    try:
        result = use_case.execute(
            UpdateContactCommand(
                organization_id=auth.organization_id,
                contact_id=contact_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(exclude_unset=True),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactAlreadyDeletedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContactNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContactEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_contact(
    contact_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteContactUseCase = Depends(get_delete_contact_use_case),
) -> ContactResponse:
    try:
        result = use_case.execute(
            DeleteContactCommand(
                organization_id=auth.organization_id,
                contact_id=contact_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)
