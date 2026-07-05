from typing import Any, Protocol
from uuid import UUID

from app.modules.mail_templates.domain.entities import MailTemplate


class MailTemplateRepository(Protocol):
    def add(self, template: MailTemplate) -> MailTemplate: ...

    def update(self, template: MailTemplate) -> MailTemplate: ...

    def get_by_id(self, organization_id: UUID, template_id: UUID) -> MailTemplate | None: ...

    def get_by_key(self, organization_id: UUID, key: str) -> MailTemplate | None: ...

    def list_by_organization(self, organization_id: UUID) -> list[MailTemplate]: ...

    def clear_default_for_type_language(
        self,
        organization_id: UUID,
        template_type: str,
        language: str,
        *,
        exclude_template_id: UUID | None = None,
    ) -> None: ...

    def flush(self) -> None: ...


class MailTemplateRenderer(Protocol):
    def render(self, template: str, variables: dict[str, Any]) -> str: ...
