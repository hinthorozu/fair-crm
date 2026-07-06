from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.application.commands import CustomerResult, UpdateCustomerCommand
from app.modules.customers.application.communication_resolver import resolve_update_communications
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.application.mappers import customer_to_result
from app.modules.customers.domain.exceptions import CustomerNotFoundError
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_UPDATE = "fair_crm.customers.update"


class UpdateCustomerUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        communication_sync: CustomerCommunicationSyncService,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._communication_sync = communication_sync
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateCustomerCommand) -> CustomerResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        customer = self._repository.get_by_id(command.organization_id, command.customer_id)
        if customer is None:
            raise CustomerNotFoundError("Customer not found")

        phones, emails, websites, sync_phone, sync_email, sync_website = resolve_update_communications(
            command
        )

        now = datetime.now(tz=UTC)
        customer.update_fields(
            display_name=command.display_name,
            legal_name=command.legal_name,
            trade_name=command.trade_name,
            customer_type=command.customer_type,
            status=command.status,
            tax_number=command.tax_number,
            tax_office=command.tax_office,
            country=command.country,
            city=command.city,
            district=command.district,
            address=command.address,
            description=command.description,
            instagram_url=command.instagram_url,
            facebook_url=command.facebook_url,
            linkedin_url=command.linkedin_url,
            youtube_url=command.youtube_url if "youtube_url" in command.fields_set else None,
            source=command.source if "source" in command.fields_set else None,
            email_allowed=command.email_allowed if "email_allowed" in command.fields_set else None,
            sms_allowed=command.sms_allowed if "sms_allowed" in command.fields_set else None,
            consent_note=command.consent_note if "consent_note" in command.fields_set else None,
            now=now,
        )

        saved = self._repository.update(customer)
        communications = self._communication_sync.sync_from_value_lists(
            organization_id=command.organization_id,
            customer_id=saved.id,
            now=now,
            phones=phones,
            emails=emails,
            websites=websites,
            sync_phone=sync_phone,
            sync_email=sync_email,
            sync_website=sync_website,
        )
        saved = self._repository.get_by_id(command.organization_id, saved.id) or saved

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.customer.updated",
            resource_type="customer",
            resource_id=str(saved.id),
            new_values={"display_name": saved.display_name, "status": saved.status.value},
            metadata={"user_id": str(command.user_id)},
        )

        return customer_to_result(saved, communications=communications)
