from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.email_accounts.api.dependencies import (
    get_auth_context,
    get_create_email_account_use_case,
    get_delete_email_account_use_case,
    get_get_email_account_use_case,
    get_list_email_accounts_use_case,
    get_send_test_email_account_mail_use_case,
    get_set_default_email_account_use_case,
    get_update_email_account_use_case,
    require_read_permission,
)
from app.modules.email_accounts.api.schemas import (
    CreateEmailAccountRequest,
    EmailAccountListResponse,
    EmailAccountResponse,
    ErrorResponse,
    SendTestEmailAccountMailRequest,
    SendTestEmailAccountMailResponse,
    UpdateEmailAccountRequest,
)
from app.modules.smtp.application.commands import (
    CreateSmtpAccountCommand,
    DeleteSmtpAccountCommand,
    GetSmtpAccountQuery,
    ListSmtpAccountsQuery,
    SendTestSmtpMailCommand,
    SetDefaultSmtpAccountCommand,
    UpdateSmtpAccountCommand,
)
from app.modules.smtp.application.create_smtp_account import CreateSmtpAccountUseCase
from app.modules.smtp.application.delete_smtp_account import DeleteSmtpAccountUseCase
from app.modules.smtp.application.get_smtp_account import GetSmtpAccountUseCase
from app.modules.smtp.application.list_smtp_accounts import ListSmtpAccountsUseCase
from app.modules.smtp.application.send_test_smtp_mail import SendTestSmtpMailUseCase
from app.modules.smtp.application.set_default_smtp_account import SetDefaultSmtpAccountUseCase
from app.modules.smtp.application.smtp_test_debug import smtp_debug_response_enabled
from app.modules.smtp.application.update_smtp_account import UpdateSmtpAccountUseCase
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpAccountEmailError,
    InvalidSmtpAccountHostError,
    InvalidSmtpAccountNameError,
    InvalidSmtpAccountPortError,
    InvalidSmtpEncryptionTypeError,
    InvalidSmtpTestRecipientError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotDefaultEligibleError,
    SmtpAccountNotFoundError,
)

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])
bearer_scheme = HTTPBearer(auto_error=False)

_SMTP_COMMAND_FIELDS = frozenset(
    {
        "name",
        "from_email",
        "from_name",
        "host",
        "port",
        "username",
        "password",
        "encryption_type",
        "is_default",
        "is_active",
        "max_delivery_attempts",
    }
)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _smtp_fields(data: dict) -> dict:
    return {key: value for key, value in data.items() if key in _SMTP_COMMAND_FIELDS}


def _to_response(result) -> EmailAccountResponse:
    data = result.__dict__.copy()
    data["config_warnings"] = list(data.get("config_warnings") or ())
    data.setdefault("account_type", "smtp")
    data.setdefault("provider_key", None)
    return EmailAccountResponse.model_validate(data)


def _to_test_mail_response(result) -> SendTestEmailAccountMailResponse:
    data = {
        "success": result.success,
        "message": result.message,
        "config_warnings": list(result.config_warnings or ()),
    }
    if smtp_debug_response_enabled():
        data.update(
            {
                "debug_error_type": result.debug_error_type,
                "debug_error_message": result.debug_error_message,
                "smtp_host": result.smtp_host,
                "smtp_port": result.smtp_port,
                "encryption_type": result.encryption_type,
            }
        )
    return SendTestEmailAccountMailResponse.model_validate(data)


@router.post(
    "",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def create_email_account(
    body: CreateEmailAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateSmtpAccountUseCase = Depends(get_create_email_account_use_case),
) -> EmailAccountResponse:
    try:
        result = use_case.execute(
            CreateSmtpAccountCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **_smtp_fields(body.model_dump()),
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
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=EmailAccountListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_email_accounts(
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListSmtpAccountsUseCase = Depends(get_list_email_accounts_use_case),
) -> EmailAccountListResponse:
    result = use_case.execute(ListSmtpAccountsQuery(organization_id=auth.organization_id))
    return EmailAccountListResponse(items=[_to_response(item) for item in result.items])


@router.get(
    "/{account_id}",
    response_model=EmailAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetSmtpAccountUseCase = Depends(get_get_email_account_use_case),
) -> EmailAccountResponse:
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
    response_model=EmailAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_email_account(
    account_id: UUID,
    body: UpdateEmailAccountRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateSmtpAccountUseCase = Depends(get_update_email_account_use_case),
) -> EmailAccountResponse:
    try:
        result = use_case.execute(
            UpdateSmtpAccountCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **_smtp_fields(body.model_dump(exclude_unset=True)),
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
    response_model=EmailAccountResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def set_default_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SetDefaultSmtpAccountUseCase = Depends(get_set_default_email_account_use_case),
) -> EmailAccountResponse:
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


@router.post(
    "/{account_id}/test",
    response_model=SendTestEmailAccountMailResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def send_test_email_account_mail(
    account_id: UUID,
    body: SendTestEmailAccountMailRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SendTestSmtpMailUseCase = Depends(get_send_test_email_account_mail_use_case),
) -> SendTestEmailAccountMailResponse:
    try:
        result = use_case.execute(
            SendTestSmtpMailCommand(
                organization_id=auth.organization_id,
                account_id=account_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                recipient=body.recipient,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidSmtpTestRecipientError, SmtpAccountAlreadyDeletedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = _to_test_mail_response(result)
    if not result.success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump(exclude_none=True),
        )
    return response


@router.delete(
    "/{account_id}",
    response_model=EmailAccountResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_email_account(
    account_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteSmtpAccountUseCase = Depends(get_delete_email_account_use_case),
) -> EmailAccountResponse:
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
