from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fair_emails.application.recipient_resolution import resolve_recipients
from app.modules.fair_emails.domain.value_objects import RecipientOptions, RecipientPreviewResult
from app.modules.fair_emails.infrastructure.recipient_loader import FairBulkEmailRecipientLoader


class FairBulkEmailRecipientService:
    def __init__(self, session: Session) -> None:
        self._loader = FairBulkEmailRecipientLoader(session)

    def preview(
        self,
        organization_id: UUID,
        fair_id: UUID,
        options: RecipientOptions,
    ) -> RecipientPreviewResult:
        participations = self._loader.load_participations(organization_id, fair_id)
        candidates = []
        candidates.extend(
            self._loader.load_customer_email_candidates(organization_id, participations, options)
        )
        candidates.extend(
            self._loader.load_contact_email_candidates(organization_id, participations, options)
        )
        return resolve_recipients(candidates, options)
