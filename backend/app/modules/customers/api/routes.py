from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.customers.api.dependencies import (
    get_archive_customer_use_case,
    get_auth_context,
    get_create_customer_use_case,
    get_get_customer_use_case,
    get_list_customers_use_case,
    get_restore_customer_use_case,
    get_update_customer_use_case,
    require_read_permission,
)
from app.modules.customers.api.schemas import (
    CreateCustomerRequest,
    CustomerListResponse,
    CustomerResponse,
    ErrorResponse,
    UpdateCustomerRequest,
)
from app.modules.customers.application.archive_customer import ArchiveCustomerUseCase
from app.modules.customers.application.commands import (
    ArchiveCustomerCommand,
    CreateCustomerCommand,
    GetCustomerQuery,
    ListCustomersQuery,
    RestoreCustomerCommand,
    UpdateCustomerCommand,
)
from app.modules.customers.application.create_customer import CreateCustomerUseCase
from app.modules.customers.application.get_customer import GetCustomerUseCase
from app.modules.customers.application.list_customers import ListCustomersUseCase
from app.modules.customers.application.restore_customer import RestoreCustomerUseCase
from app.modules.customers.application.update_customer import UpdateCustomerUseCase
from app.modules.customers.domain.exceptions import (
    CustomerAlreadyArchivedError,
    CustomerNotArchivedError,
    CustomerNotFoundError,
    InvalidCustomerEmailError,
    InvalidCustomerNameError,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType

router = APIRouter(prefix="/customers", tags=["customers"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> CustomerResponse:
    return CustomerResponse.model_validate(result.__dict__)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def create_customer(
    body: CreateCustomerRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateCustomerUseCase = Depends(get_create_customer_use_case),
) -> CustomerResponse:
    try:
        result = use_case.execute(
            CreateCustomerCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(),
            )
        )
    except InvalidCustomerNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidCustomerEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=CustomerListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_customers(
    request: Request,
    customer_status: CustomerStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    customer_type: CustomerType | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListCustomersUseCase = Depends(get_list_customers_use_case),
) -> CustomerListResponse:
    raw_status = request.query_params.get("status")
    if customer_status == CustomerStatus.ARCHIVED or raw_status == CustomerStatus.ARCHIVED.value:
        list_status = CustomerStatus.ARCHIVED
        list_include_archived = True
    elif include_archived and raw_status is None and customer_status is None:
        list_status = CustomerStatus.ARCHIVED
        list_include_archived = True
    elif customer_status is not None:
        list_status = customer_status
        list_include_archived = False
    elif raw_status and raw_status != CustomerStatus.ARCHIVED.value:
        try:
            list_status = CustomerStatus(raw_status)
            list_include_archived = False
        except ValueError:
            list_status = None
            list_include_archived = False
    else:
        list_status = None
        list_include_archived = False

    result = use_case.execute(
        ListCustomersQuery(
            organization_id=auth.organization_id,
            status=list_status,
            include_archived=list_include_archived,
            customer_type=customer_type,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )
    return CustomerListResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post(
    "/{customer_id}/restore",
    response_model=CustomerResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def restore_customer(
    customer_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RestoreCustomerUseCase = Depends(get_restore_customer_use_case),
) -> CustomerResponse:
    try:
        result = use_case.execute(
            RestoreCustomerCommand(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerNotArchivedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_customer(
    customer_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetCustomerUseCase = Depends(get_get_customer_use_case),
) -> CustomerResponse:
    try:
        result = use_case.execute(
            GetCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
            )
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def update_customer(
    customer_id: UUID,
    body: UpdateCustomerRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateCustomerUseCase = Depends(get_update_customer_use_case),
) -> CustomerResponse:
    try:
        result = use_case.execute(
            UpdateCustomerCommand(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(exclude_unset=True),
            )
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerAlreadyArchivedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidCustomerNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidCustomerEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{customer_id}",
    response_model=CustomerResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def archive_customer(
    customer_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ArchiveCustomerUseCase = Depends(get_archive_customer_use_case),
) -> CustomerResponse:
    try:
        result = use_case.execute(
            ArchiveCustomerCommand(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)
