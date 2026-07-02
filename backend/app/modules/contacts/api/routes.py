from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.modules.contacts.application.list_contacts_by_customer import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
)

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
    request: Request,
    customer_id: UUID,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_by", "sort")),
    ] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_order", "sort_dir", "direction"),
        ),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListContactsByCustomerUseCase = Depends(get_list_contacts_by_customer_use_case),
) -> ContactListResponse:
    try:
        list_query = parse_list_query(
            page=page,
            page_size=resolve_page_size_from_request(request, page_size),
            search=search,
            sort=sort,
            sort_by=sort_by,
            direction=direction,
            sort_dir=sort_dir,
            default_sort=DEFAULT_SORT_FIELD,
            allowed_sort_fields=ALLOWED_SORT_FIELDS,
            default_direction=DEFAULT_SORT_DIRECTION,
        )
        result = use_case.execute(
            ListContactsByCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                search=list_query.search,
                page=list_query.page,
                page_size=list_query.page_size,
                sort_by=list_query.sort_by,
                sort_dir=list_query.sort_dir,
            )
        )
    except CustomerNotFoundForContactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filters: dict = {}
    if list_query.search:
        filters["search"] = list_query.search

    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
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
