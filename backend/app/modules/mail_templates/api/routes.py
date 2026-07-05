from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.mail_templates.api.dependencies import (
    get_auth_context,
    get_create_mail_template_use_case,
    get_delete_mail_template_use_case,
    get_get_mail_template_use_case,
    get_list_mail_templates_use_case,
    get_render_mail_template_use_case,
    get_send_test_mail_template_use_case,
    get_update_mail_template_use_case,
    require_read_permission,
)
from app.modules.mail_templates.api.schemas import (
    CreateMailTemplateRequest,
    ErrorResponse,
    MailTemplateListResponse,
    MailTemplateResponse,
    RenderMailTemplateRequest,
    RenderMailTemplateResponse,
    SendTestMailTemplateRequest,
    SendTestMailTemplateResponse,
    UpdateMailTemplateRequest,
)
from app.modules.mail_templates.application.commands import (
    CreateMailTemplateCommand,
    DeleteMailTemplateCommand,
    GetMailTemplateQuery,
    ListMailTemplatesQuery,
    RenderMailTemplateCommand,
    SendTestMailTemplateCommand,
    UpdateMailTemplateCommand,
)
from app.modules.mail_templates.application.create_mail_template import CreateMailTemplateUseCase
from app.modules.mail_templates.application.delete_mail_template import DeleteMailTemplateUseCase
from app.modules.mail_templates.application.get_mail_template import GetMailTemplateUseCase
from app.modules.mail_templates.application.list_mail_templates import ListMailTemplatesUseCase
from app.modules.mail_templates.application.render_mail_template import RenderMailTemplateUseCase
from app.modules.mail_templates.application.send_test_mail_template import SendTestMailTemplateUseCase
from app.modules.mail_templates.application.update_mail_template import UpdateMailTemplateUseCase
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.modules.mail_templates.domain.exceptions import (
    InvalidMailTemplateKeyError,
    InvalidMailTemplateLanguageError,
    InvalidMailTemplateNameError,
    InvalidMailTemplateSubjectError,
    InvalidMailTemplateTestRecipientError,
    InvalidMailTemplateTestSubjectError,
    InvalidMailTemplateTypeError,
    MailTemplateAlreadyDeletedError,
    MailTemplateDefaultAlreadyExistsError,
    MailTemplateDefaultSmtpNotFoundError,
    MailTemplateInactiveForTestError,
    MailTemplateKeyAlreadyExistsError,
    MailTemplateNotDefaultEligibleError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)

router = APIRouter(prefix="/mail-templates", tags=["mail-templates"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> MailTemplateResponse:
    return MailTemplateResponse.model_validate(result.__dict__)


@router.post(
    "",
    response_model=MailTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def create_mail_template(
    body: CreateMailTemplateRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateMailTemplateUseCase = Depends(get_create_mail_template_use_case),
) -> MailTemplateResponse:
    try:
        result = use_case.execute(
            CreateMailTemplateCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MailTemplateKeyAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MailTemplateDefaultAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        InvalidMailTemplateNameError,
        InvalidMailTemplateKeyError,
        InvalidMailTemplateSubjectError,
        InvalidMailTemplateTypeError,
        InvalidMailTemplateLanguageError,
        MailTemplateNotDefaultEligibleError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=MailTemplateListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_mail_templates(
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListMailTemplatesUseCase = Depends(get_list_mail_templates_use_case),
) -> MailTemplateListResponse:
    result = use_case.execute(ListMailTemplatesQuery(organization_id=auth.organization_id))
    return MailTemplateListResponse(items=[_to_response(item) for item in result.items])


@router.get(
    "/{template_id}",
    response_model=MailTemplateResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_mail_template(
    template_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetMailTemplateUseCase = Depends(get_get_mail_template_use_case),
) -> MailTemplateResponse:
    try:
        result = use_case.execute(
            GetMailTemplateQuery(
                organization_id=auth.organization_id,
                template_id=template_id,
            )
        )
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{template_id}",
    response_model=MailTemplateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def update_mail_template(
    template_id: UUID,
    body: UpdateMailTemplateRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateMailTemplateUseCase = Depends(get_update_mail_template_use_case),
) -> MailTemplateResponse:
    try:
        result = use_case.execute(
            UpdateMailTemplateCommand(
                organization_id=auth.organization_id,
                template_id=template_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                **body.model_dump(exclude_unset=True),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MailTemplateKeyAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MailTemplateDefaultAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        InvalidMailTemplateNameError,
        InvalidMailTemplateKeyError,
        InvalidMailTemplateSubjectError,
        InvalidMailTemplateTypeError,
        InvalidMailTemplateLanguageError,
        MailTemplateNotDefaultEligibleError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{template_id}",
    response_model=MailTemplateResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_mail_template(
    template_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteMailTemplateUseCase = Depends(get_delete_mail_template_use_case),
) -> MailTemplateResponse:
    try:
        result = use_case.execute(
            DeleteMailTemplateCommand(
                organization_id=auth.organization_id,
                template_id=template_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.post(
    "/{template_id}/render",
    response_model=RenderMailTemplateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def render_mail_template(
    template_id: UUID,
    body: RenderMailTemplateRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RenderMailTemplateUseCase = Depends(get_render_mail_template_use_case),
) -> RenderMailTemplateResponse:
    try:
        result = use_case.execute(
            RenderMailTemplateCommand(
                organization_id=auth.organization_id,
                template_id=template_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                variables=body.variables,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MailTemplateAlreadyDeletedError, MailTemplateRenderError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RenderMailTemplateResponse(
        subject=result.subject,
        body_html=result.body_html,
        body_text=result.body_text,
    )


@router.post(
    "/{template_id}/test-email",
    response_model=SendTestMailTemplateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def send_test_mail_template(
    template_id: UUID,
    body: SendTestMailTemplateRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: SendTestMailTemplateUseCase = Depends(get_send_test_mail_template_use_case),
) -> SendTestMailTemplateResponse:
    try:
        result = use_case.execute(
            SendTestMailTemplateCommand(
                organization_id=auth.organization_id,
                template_id=template_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                to_email=body.to_email,
                smtp_account_id=body.smtp_account_id,
                variables=body.variables,
                subject_override=body.subject_override,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        InvalidMailTemplateTestRecipientError,
        InvalidMailTemplateTestSubjectError,
        MailTemplateAlreadyDeletedError,
        MailTemplateDefaultSmtpNotFoundError,
        MailTemplateInactiveForTestError,
        MailTemplateRenderError,
        SmtpAccountAlreadyDeletedError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = SendTestMailTemplateResponse.model_validate(result.__dict__)
    if not result.success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump(exclude_none=True),
        )
    return response
