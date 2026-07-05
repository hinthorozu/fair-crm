from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.smtp.api.dependencies import (
    get_auth_context,
    get_create_smtp_account_use_case,
    get_delete_smtp_account_use_case,
    get_get_smtp_account_use_case,
    get_list_smtp_accounts_use_case,
    get_set_default_smtp_account_use_case,
    get_update_smtp_account_use_case,
    require_read_permission,
)
from app.modules.smtp.api.schemas import (
    CreateSmtpAccountRequest,
    ErrorResponse,
    SmtpAccountListResponse,
    SmtpAccountResponse,
    UpdateSmtpAccountRequest,
)
from app.modules.smtp.application.commands import (
    CreateSmtpAccountCommand,
    DeleteSmtpAccountCommand,
    GetSmtpAccountQuery,
    ListSmtpAccountsQuery,
    SetDefaultSmtpAccountCommand,
    UpdateSmtpAccountCommand,
)
from app.modules.smtp.application.create_smtp_account import CreateSmtpAccountUseCase
from app.modules.smtp.application.delete_smtp_account import DeleteSmtpAccountUseCase
from app.modules.smtp.application.get_smtp_account import GetSmtpAccountUseCase
from app.modules.smtp.application.list_smtp_accounts import ListSmtpAccountsUseCase
from app.modules.smtp.application.set_default_smtp_account import SetDefaultSmtpAccountUseCase
from app.modules.smtp.application.update_smtp_account import UpdateSmtpAccountUseCase
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpAccountEmailError,
    InvalidSmtpAccountHostError,
    InvalidSmtpAccountNameError,
    InvalidSmtpAccountPortError,
    InvalidSmtpEncryptionTypeError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotDefaultEligibleError,
    SmtpAccountNotFoundError,
)

router = APIRouter(prefix="/smtp/accounts", tags=["smtp"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> SmtpAccountResponse:
    return SmtpAccountResponse.model_validate(result.__dict__)


@router.post(
    "",
    response_model=SmtpAccountResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def create_smtp_account(
    body: CreateSmtpAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateSmtpAccountUseCase = Depends(get_create_smtp_account_use_case),
) -> SmtpAccountResponse:
    try:
        result = use_case.execute(
            CreateSmtpAccountCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (
        InvalidSmtpAccountNameError,
        InvalidSmtpAccountEmailError,
        InvalidSmtpAccountHostError,
        InvalidSmtpAccountPortError,
        InvalidSmtpEncryptionTypeError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=SmtpAccountListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_smtp_accounts(
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListSmtpAccountsUseCase = Depends(get_list_smtp_accounts_use_case),
) -> SmtpAccountListResponse:
    result = use_case.execute(ListSmtpAccountsQuery(organization_id=auth.organization_id))
    return SmtpAccountListResponse(items=[_to_response(item) for item in result.items])


@router.get(
    "/{account_id}",
    response_model=SmtpAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_smtp_account(
    account_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetSmtpAccountUseCase = Depends(get_get_smtp_account_use_case),
) -> SmtpAccountResponse:
    try:
        result = use_case.execute(
            GetSmtpAccountQuery(
                organization_id=auth.organization_id,
                account_id=account_id,
            )
        )
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{account_id}",
    response_model=SmtpAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_smtp_account(
    account_id: UUID,
    body: UpdateSmtpAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateSmtpAccountUseCase = Depends(get_update_smtp_account_use_case),
) -> SmtpAccountResponse:
    try:
        result = use_case.execute(
            UpdateSmtpAccountCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(exclude_unset=True),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SmtpAccountAlreadyDeletedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (
        InvalidSmtpAccountNameError,
        InvalidSmtpAccountEmailError,
        InvalidSmtpAccountHostError,
        InvalidSmtpAccountPortError,
        InvalidSmtpEncryptionTypeError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.post(
    "/{account_id}/set-default",
    response_model=SmtpAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def set_default_smtp_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SetDefaultSmtpAccountUseCase = Depends(get_set_default_smtp_account_use_case),
) -> SmtpAccountResponse:
    try:
        result = use_case.execute(
            SetDefaultSmtpAccountCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (SmtpAccountAlreadyDeletedError, SmtpAccountNotDefaultEligibleError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{account_id}",
    response_model=SmtpAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_smtp_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteSmtpAccountUseCase = Depends(get_delete_smtp_account_use_case),
) -> SmtpAccountResponse:
    try:
        result = use_case.execute(
            DeleteSmtpAccountCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)
