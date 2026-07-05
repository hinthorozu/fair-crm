from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.commands import PreviewRecipientsQuery
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.domain.exceptions import FairNotEligibleForBulkEmailError
from app.modules.fair_emails.domain.value_objects import RecipientPreviewResult
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository

PERMISSION_PREVIEW = "fair_crm.fair_emails.preview"


class PreviewFairEmailRecipientsUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        recipient_service: FairBulkEmailRecipientService,
        authorization: AuthorizationPort,
    ) -> None:
        self._fair_repository = fair_repository
        self._recipient_service = recipient_service
        self._authorization = authorization

    def execute(self, query: PreviewRecipientsQuery) -> RecipientPreviewResult:
        if not self._authorization.check_permission(
            organization_id=query.organization_id,
            user_id=query.user_id,
            permission_code=PERMISSION_PREVIEW,
            access_token=query.access_token,
        ):
            raise ForbiddenError("Permission denied")

        fair = self._fair_repository.get_by_id(query.organization_id, query.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.deleted_at is not None:
            raise FairNotEligibleForBulkEmailError("Arşivlenmiş fuar için toplu mail gönderilemez.")

        return self._recipient_service.preview(
            query.organization_id,
            query.fair_id,
            query.recipient_options,
        )
