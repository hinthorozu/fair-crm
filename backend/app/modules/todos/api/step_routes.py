from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.todos.api.dependencies import get_auth_context, require_read_permission
from app.modules.todos.api.step_dependencies import (
    get_delete_todo_step_use_case,
    get_list_todo_steps_use_case,
    get_replace_todo_steps_use_case,
    get_update_todo_step_use_case,
)
from app.modules.todos.api.step_schemas import (
    ErrorResponse,
    ReplaceTodoStepsRequest,
    TodoStepResponse,
    UpdateTodoStepRequest,
)
from app.modules.todos.application.delete_todo_step import DeleteTodoStepUseCase
from app.modules.todos.application.list_todo_steps import ListTodoStepsUseCase
from app.modules.todos.application.replace_todo_steps import ReplaceTodoStepsUseCase
from app.modules.todos.application.step_commands import (
    DeleteTodoStepCommand,
    ListTodoStepsQuery,
    ReplaceTodoStepsCommand,
    TodoStepReplaceItem,
    UpdateTodoStepCommand,
)
from app.modules.todos.application.update_todo_step import UpdateTodoStepUseCase
from app.modules.todos.domain.exceptions import (
    InvalidTodoStepTitleError,
    TodoNotFoundError,
    TodoStepNotFoundError,
)

router = APIRouter(prefix="/todos/{todo_id}/steps", tags=["todo-steps"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> TodoStepResponse:
    return TodoStepResponse.model_validate(asdict(result))


@router.get(
    "",
    response_model=list[TodoStepResponse],
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def list_todo_steps(
    todo_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ListTodoStepsUseCase = Depends(get_list_todo_steps_use_case),
) -> list[TodoStepResponse]:
    try:
        results = use_case.execute(
            ListTodoStepsQuery(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                todo_id=todo_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_to_response(item) for item in results]


@router.put(
    "",
    response_model=list[TodoStepResponse],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def replace_todo_steps(
    todo_id: UUID,
    body: ReplaceTodoStepsRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ReplaceTodoStepsUseCase = Depends(get_replace_todo_steps_use_case),
) -> list[TodoStepResponse]:
    try:
        results = use_case.execute(
            ReplaceTodoStepsCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                todo_id=todo_id,
                steps=[
                    TodoStepReplaceItem(id=item.id, title=item.title) for item in body.steps
                ],
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTodoStepTitleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [_to_response(item) for item in results]


@router.patch(
    "/{step_id}",
    response_model=TodoStepResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def update_todo_step(
    todo_id: UUID,
    step_id: UUID,
    body: UpdateTodoStepRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateTodoStepUseCase = Depends(get_update_todo_step_use_case),
) -> TodoStepResponse:
    payload = body.model_dump(exclude_unset=True)
    try:
        result = use_case.execute(
            UpdateTodoStepCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                todo_id=todo_id,
                step_id=step_id,
                title=payload.get("title"),
                is_completed=payload.get("is_completed"),
                set_title="title" in payload,
                set_is_completed="is_completed" in payload,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (TodoNotFoundError, TodoStepNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTodoStepTitleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def delete_todo_step(
    todo_id: UUID,
    step_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteTodoStepUseCase = Depends(get_delete_todo_step_use_case),
) -> Response:
    try:
        use_case.execute(
            DeleteTodoStepCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                todo_id=todo_id,
                step_id=step_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (TodoNotFoundError, TodoStepNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
