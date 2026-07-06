from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.infrastructure.persistence.models import ContactModel


def model_to_entity(model: ContactModel) -> Contact:
    return Contact(
        id=model.id,
        organization_id=model.organization_id,
        customer_id=model.customer_id,
        first_name=model.first_name,
        last_name=model.last_name,
        title=model.title,
        department=model.department,
        email=model.email,
        phone=model.phone,
        mobile_phone=model.mobile_phone,
        linkedin=model.linkedin,
        notes=model.notes,
        is_primary=model.is_primary,
        is_active=model.is_active,
        email_allowed=model.email_allowed,
        sms_allowed=model.sms_allowed,
        email_unsubscribed_at=model.email_unsubscribed_at,
        sms_unsubscribed_at=model.sms_unsubscribed_at,
        consent_note=model.consent_note,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(contact: Contact) -> ContactModel:
    return ContactModel(
        id=contact.id,
        organization_id=contact.organization_id,
        customer_id=contact.customer_id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        title=contact.title,
        department=contact.department,
        email=contact.email,
        phone=contact.phone,
        mobile_phone=contact.mobile_phone,
        linkedin=contact.linkedin,
        notes=contact.notes,
        is_primary=contact.is_primary,
        is_active=contact.is_active,
        email_allowed=contact.email_allowed,
        sms_allowed=contact.sms_allowed,
        email_unsubscribed_at=contact.email_unsubscribed_at,
        sms_unsubscribed_at=contact.sms_unsubscribed_at,
        consent_note=contact.consent_note,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        deleted_at=contact.deleted_at,
    )


def update_model_from_entity(model: ContactModel, contact: Contact) -> None:
    model.first_name = contact.first_name
    model.last_name = contact.last_name
    model.title = contact.title
    model.department = contact.department
    model.email = contact.email
    model.phone = contact.phone
    model.mobile_phone = contact.mobile_phone
    model.linkedin = contact.linkedin
    model.notes = contact.notes
    model.is_primary = contact.is_primary
    model.is_active = contact.is_active
    model.email_allowed = contact.email_allowed
    model.sms_allowed = contact.sms_allowed
    model.email_unsubscribed_at = contact.email_unsubscribed_at
    model.sms_unsubscribed_at = contact.sms_unsubscribed_at
    model.consent_note = contact.consent_note
    model.updated_at = contact.updated_at
    model.deleted_at = contact.deleted_at
