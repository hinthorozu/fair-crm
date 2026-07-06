from app.modules.contacts.application.commands import ContactResult
from app.modules.contacts.domain.entities import Contact


def contact_to_result(contact: Contact) -> ContactResult:
    return ContactResult(
        id=contact.id,
        organization_id=contact.organization_id,
        customer_id=contact.customer_id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        full_name=contact.full_name,
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
