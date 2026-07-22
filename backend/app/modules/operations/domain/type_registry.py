from dataclasses import dataclass, field
from typing import Any

from app.modules.operations.domain.exceptions import InvalidOperationTypeError
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationType,
    SourceKind,
)


@dataclass(frozen=True)
class WizardStepDefinition:
    id: str
    required: bool = True
    order: int = 0


@dataclass(frozen=True)
class OperationTypeDefinition:
    type: str
    label_key: str
    description_key: str
    supported_sources: tuple[str, ...]
    default_source: str
    capabilities: HandlerCapabilities
    wizard_steps: tuple[WizardStepDefinition, ...]
    type_config_schema: dict[str, Any] = field(default_factory=dict)
    run_settings_schema: dict[str, Any] = field(default_factory=dict)
    available_in_wizard: bool = True


_DEFAULT_WIZARD_STEPS = (
    WizardStepDefinition(id="type", required=True, order=1),
    WizardStepDefinition(id="source", required=True, order=2),
    WizardStepDefinition(id="type_config", required=True, order=3),
    WizardStepDefinition(id="scope", required=True, order=4),
    WizardStepDefinition(id="run_settings", required=False, order=5),
    WizardStepDefinition(id="summary", required=True, order=6),
    WizardStepDefinition(id="confirm", required=True, order=7),
)

_MANUAL_TASK_STEPS = (
    WizardStepDefinition(id="type", required=True, order=1),
    WizardStepDefinition(id="source", required=False, order=2),
    WizardStepDefinition(id="type_config", required=True, order=3),
    WizardStepDefinition(id="scope", required=False, order=4),
    WizardStepDefinition(id="run_settings", required=False, order=5),
    WizardStepDefinition(id="summary", required=True, order=6),
    WizardStepDefinition(id="confirm", required=True, order=7),
)


def _placeholder_capabilities(*, supports_schedule: bool = False) -> HandlerCapabilities:
    return HandlerCapabilities(
        supports_pause=False,
        supports_resume=False,
        supports_retry=False,
        supports_schedule=supports_schedule,
        supports_items=True,
        requires_worker=True,
        execution_ready=False,
    )


OPERATION_TYPE_DEFINITIONS: dict[str, OperationTypeDefinition] = {
    OperationType.SCRAPER: OperationTypeDefinition(
        type=OperationType.SCRAPER,
        label_key="scraper",
        description_key="scraper_description",
        supported_sources=(SourceKind.FAIR, SourceKind.NONE),
        default_source=SourceKind.FAIR,
        capabilities=_placeholder_capabilities(),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={
            "fields": ["adapter_key", "source_url", "scraper_config"],
        },
        run_settings_schema={
            "fields": ["retry", "rate_limit", "concurrency", "priority"],
        },
        available_in_wizard=True,
    ),
    OperationType.EMAIL: OperationTypeDefinition(
        type=OperationType.EMAIL,
        label_key="email",
        description_key="email_description",
        supported_sources=(
            SourceKind.CUSTOMER,
            SourceKind.MANUAL_SELECTION,
            SourceKind.NONE,
        ),
        default_source=SourceKind.CUSTOMER,
        capabilities=_placeholder_capabilities(supports_schedule=True),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={
            "fields": ["smtp_account_id", "template_id", "subject"],
        },
        run_settings_schema={
            "fields": ["retry", "rate_limit", "schedule", "priority"],
        },
    ),
    OperationType.BULK_EMAIL: OperationTypeDefinition(
        type=OperationType.BULK_EMAIL,
        label_key="bulk_email",
        description_key="bulk_email_description",
        supported_sources=(
            SourceKind.FAIR,
            SourceKind.SEGMENT,
            SourceKind.MANUAL_SELECTION,
            SourceKind.IMPORT,
        ),
        default_source=SourceKind.FAIR,
        capabilities=_placeholder_capabilities(supports_schedule=True),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={
            "fields": ["smtp_account_id", "template_id", "subject"],
        },
        run_settings_schema={
            "fields": ["retry", "rate_limit", "schedule", "concurrency", "priority"],
        },
    ),
    OperationType.ENRICHMENT: OperationTypeDefinition(
        type=OperationType.ENRICHMENT,
        label_key="enrichment",
        description_key="enrichment_description",
        supported_sources=(
            SourceKind.FAIR,
            SourceKind.SEGMENT,
            SourceKind.MANUAL_SELECTION,
            SourceKind.CUSTOMER,
        ),
        default_source=SourceKind.FAIR,
        capabilities=_placeholder_capabilities(),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={
            "fields": ["research_website", "research_email", "research_phone"],
        },
        run_settings_schema={
            "fields": ["retry", "rate_limit", "concurrency", "priority"],
        },
    ),
    OperationType.DUPLICATE_CHECK: OperationTypeDefinition(
        type=OperationType.DUPLICATE_CHECK,
        label_key="duplicate_check",
        description_key="duplicate_check_description",
        supported_sources=(
            SourceKind.SEGMENT,
            SourceKind.MANUAL_SELECTION,
            SourceKind.NONE,
        ),
        default_source=SourceKind.NONE,
        capabilities=_placeholder_capabilities(),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={"fields": ["match_fields", "normalize_rules"]},
        run_settings_schema={"fields": ["concurrency", "priority"]},
    ),
    OperationType.DATA_CLEANUP: OperationTypeDefinition(
        type=OperationType.DATA_CLEANUP,
        label_key="data_cleanup",
        description_key="data_cleanup_description",
        supported_sources=(
            SourceKind.SEGMENT,
            SourceKind.MANUAL_SELECTION,
            SourceKind.NONE,
        ),
        default_source=SourceKind.NONE,
        capabilities=_placeholder_capabilities(),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={"fields": ["cleanup_rules"]},
        run_settings_schema={"fields": ["retry", "concurrency", "priority"]},
    ),
    OperationType.WHATSAPP: OperationTypeDefinition(
        type=OperationType.WHATSAPP,
        label_key="whatsapp",
        description_key="whatsapp_description",
        supported_sources=(
            SourceKind.FAIR,
            SourceKind.SEGMENT,
            SourceKind.MANUAL_SELECTION,
            SourceKind.CUSTOMER,
        ),
        default_source=SourceKind.CUSTOMER,
        capabilities=_placeholder_capabilities(supports_schedule=True),
        wizard_steps=_DEFAULT_WIZARD_STEPS,
        type_config_schema={
            "fields": ["provider", "template_id", "message"],
        },
        run_settings_schema={
            "fields": ["retry", "rate_limit", "schedule", "priority"],
        },
    ),
    OperationType.MANUAL_TASK: OperationTypeDefinition(
        type=OperationType.MANUAL_TASK,
        label_key="manual_task",
        description_key="manual_task_description",
        supported_sources=(SourceKind.CUSTOMER, SourceKind.NONE, SourceKind.FAIR),
        default_source=SourceKind.CUSTOMER,
        capabilities=HandlerCapabilities(
            supports_pause=False,
            supports_resume=False,
            supports_retry=False,
            supports_schedule=True,
            supports_items=False,
            requires_worker=False,
            execution_ready=True,
        ),
        wizard_steps=_MANUAL_TASK_STEPS,
        type_config_schema={
            "fields": [
                "title",
                "description",
                "note",
                "due_at",
                "assignee_user_id",
                "assigned_user_id",
                "priority",
                "customer_id",
            ],
        },
        run_settings_schema={"fields": ["schedule", "priority"]},
    ),
    OperationType.REMINDER: OperationTypeDefinition(
        type=OperationType.REMINDER,
        label_key="reminder",
        description_key="reminder_description",
        supported_sources=(SourceKind.CUSTOMER, SourceKind.NONE),
        default_source=SourceKind.NONE,
        capabilities=_placeholder_capabilities(supports_schedule=True),
        wizard_steps=_MANUAL_TASK_STEPS,
        type_config_schema={"fields": ["message", "remind_at", "customer_id"]},
        run_settings_schema={"fields": ["schedule", "priority"]},
    ),
}


class OperationTypeRegistry:
    def __init__(self, definitions: dict[str, OperationTypeDefinition] | None = None) -> None:
        self._definitions = dict(definitions or OPERATION_TYPE_DEFINITIONS)

    def get(self, operation_type: str) -> OperationTypeDefinition | None:
        return self._definitions.get(operation_type)

    def require(self, operation_type: str) -> OperationTypeDefinition:
        definition = self.get(operation_type)
        if definition is None:
            raise InvalidOperationTypeError(f"Unknown operation type: {operation_type}")
        return definition

    def list_all(self) -> list[OperationTypeDefinition]:
        return list(self._definitions.values())

    def list_wizard_types(self) -> list[OperationTypeDefinition]:
        return [item for item in self._definitions.values() if item.available_in_wizard]


default_operation_type_registry = OperationTypeRegistry()
