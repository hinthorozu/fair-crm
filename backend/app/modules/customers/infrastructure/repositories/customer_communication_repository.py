from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.customers.domain.communication_entities import (
    CustomerCommunicationListSummary,
    CustomerCommunications,
    CustomerEmail,
    CustomerPhone,
    CustomerWebsite,
)
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)


class SqlAlchemyCustomerCommunicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_for_customer(self, customer_id: UUID) -> CustomerCommunications:
        phones = (
            self._session.query(CustomerPhoneModel)
            .filter(CustomerPhoneModel.customer_id == customer_id)
            .order_by(CustomerPhoneModel.is_primary.desc(), CustomerPhoneModel.created_at.asc())
            .all()
        )
        emails = (
            self._session.query(CustomerEmailModel)
            .filter(CustomerEmailModel.customer_id == customer_id)
            .order_by(CustomerEmailModel.is_primary.desc(), CustomerEmailModel.created_at.asc())
            .all()
        )
        websites = (
            self._session.query(CustomerWebsiteModel)
            .filter(CustomerWebsiteModel.customer_id == customer_id)
            .order_by(CustomerWebsiteModel.is_primary.desc(), CustomerWebsiteModel.created_at.asc())
            .all()
        )
        return CustomerCommunications(
            phones=[self._phone_to_entity(model) for model in phones],
            emails=[self._email_to_entity(model) for model in emails],
            websites=[self._website_to_entity(model) for model in websites],
        )

    def load_list_summaries(
        self,
        customer_ids: list[UUID],
    ) -> dict[UUID, CustomerCommunicationListSummary]:
        if not customer_ids:
            return {}

        phone_by_customer = self._list_value_summaries(
            customer_ids,
            model=CustomerPhoneModel,
            value_attr="phone",
        )
        email_by_customer = self._list_value_summaries(
            customer_ids,
            model=CustomerEmailModel,
            value_attr="email",
        )
        website_by_customer = self._list_value_summaries(
            customer_ids,
            model=CustomerWebsiteModel,
            value_attr="website",
        )

        summaries: dict[UUID, CustomerCommunicationListSummary] = {}
        for customer_id in customer_ids:
            phone_value, phone_extra = phone_by_customer.get(customer_id, (None, 0))
            email_value, email_extra = email_by_customer.get(customer_id, (None, 0))
            website_value, website_extra = website_by_customer.get(customer_id, (None, 0))
            summaries[customer_id] = CustomerCommunicationListSummary(
                phone=phone_value,
                phone_extra_count=phone_extra,
                email=email_value,
                email_extra_count=email_extra,
                website=website_value,
                website_extra_count=website_extra,
            )
        return summaries

    def _list_value_summaries(
        self,
        customer_ids: list[UUID],
        *,
        model: type[CustomerPhoneModel] | type[CustomerEmailModel] | type[CustomerWebsiteModel],
        value_attr: str,
    ) -> dict[UUID, tuple[str | None, int]]:
        rows = (
            self._session.query(model)
            .filter(model.customer_id.in_(customer_ids))
            .order_by(
                model.customer_id,
                model.is_primary.desc(),
                model.created_at.asc(),
            )
            .all()
        )
        grouped: dict[UUID, list] = defaultdict(list)
        for row in rows:
            grouped[row.customer_id].append(row)

        summaries: dict[UUID, tuple[str | None, int]] = {}
        for customer_id, items in grouped.items():
            primary_value = getattr(items[0], value_attr)
            summaries[customer_id] = (primary_value, max(len(items) - 1, 0))
        return summaries

    def load_for_customers(self, customer_ids: list[UUID]) -> dict[UUID, CustomerCommunications]:
        if not customer_ids:
            return {}

        phones = (
            self._session.query(CustomerPhoneModel)
            .filter(CustomerPhoneModel.customer_id.in_(customer_ids))
            .order_by(
                CustomerPhoneModel.customer_id,
                CustomerPhoneModel.is_primary.desc(),
                CustomerPhoneModel.created_at.asc(),
            )
            .all()
        )
        emails = (
            self._session.query(CustomerEmailModel)
            .filter(CustomerEmailModel.customer_id.in_(customer_ids))
            .order_by(
                CustomerEmailModel.customer_id,
                CustomerEmailModel.is_primary.desc(),
                CustomerEmailModel.created_at.asc(),
            )
            .all()
        )
        websites = (
            self._session.query(CustomerWebsiteModel)
            .filter(CustomerWebsiteModel.customer_id.in_(customer_ids))
            .order_by(
                CustomerWebsiteModel.customer_id,
                CustomerWebsiteModel.is_primary.desc(),
                CustomerWebsiteModel.created_at.asc(),
            )
            .all()
        )

        phone_map: dict[UUID, list[CustomerPhone]] = defaultdict(list)
        email_map: dict[UUID, list[CustomerEmail]] = defaultdict(list)
        website_map: dict[UUID, list[CustomerWebsite]] = defaultdict(list)

        for model in phones:
            phone_map[model.customer_id].append(self._phone_to_entity(model))
        for model in emails:
            email_map[model.customer_id].append(self._email_to_entity(model))
        for model in websites:
            website_map[model.customer_id].append(self._website_to_entity(model))

        return {
            customer_id: CustomerCommunications(
                phones=phone_map.get(customer_id, []),
                emails=email_map.get(customer_id, []),
                websites=website_map.get(customer_id, []),
            )
            for customer_id in customer_ids
        }

    def replace_phones(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        phones: list[str],
        now: datetime,
    ) -> list[CustomerPhone]:
        self._session.query(CustomerPhoneModel).filter(
            CustomerPhoneModel.customer_id == customer_id,
        ).delete(synchronize_session=False)

        created: list[CustomerPhone] = []
        for index, phone in enumerate(phones):
            model = CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer_id,
                phone=phone,
                is_primary=index == 0,
                created_at=now,
            )
            self._session.add(model)
            created.append(self._phone_to_entity(model))
        return created

    def replace_emails(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        emails: list[str],
        now: datetime,
    ) -> list[CustomerEmail]:
        self._session.query(CustomerEmailModel).filter(
            CustomerEmailModel.customer_id == customer_id,
        ).delete(synchronize_session=False)

        created: list[CustomerEmail] = []
        for index, email in enumerate(emails):
            model = CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer_id,
                email=email,
                is_primary=index == 0,
                created_at=now,
            )
            self._session.add(model)
            created.append(self._email_to_entity(model))
        return created

    def replace_websites(
        self,
        *,
        organization_id: UUID,
        customer_id: UUID,
        websites: list[str],
        now: datetime,
    ) -> list[CustomerWebsite]:
        self._session.query(CustomerWebsiteModel).filter(
            CustomerWebsiteModel.customer_id == customer_id,
        ).delete(synchronize_session=False)

        created: list[CustomerWebsite] = []
        for index, website in enumerate(websites):
            model = CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer_id,
                website=website,
                is_primary=index == 0,
                created_at=now,
            )
            self._session.add(model)
            created.append(self._website_to_entity(model))
        return created

    @staticmethod
    def _phone_to_entity(model: CustomerPhoneModel) -> CustomerPhone:
        return CustomerPhone(
            id=model.id,
            customer_id=model.customer_id,
            phone=model.phone,
            is_primary=model.is_primary,
            created_at=model.created_at,
        )

    @staticmethod
    def _email_to_entity(model: CustomerEmailModel) -> CustomerEmail:
        return CustomerEmail(
            id=model.id,
            customer_id=model.customer_id,
            email=model.email,
            is_primary=model.is_primary,
            created_at=model.created_at,
        )

    @staticmethod
    def _website_to_entity(model: CustomerWebsiteModel) -> CustomerWebsite:
        return CustomerWebsite(
            id=model.id,
            customer_id=model.customer_id,
            website=model.website,
            is_primary=model.is_primary,
            created_at=model.created_at,
        )
