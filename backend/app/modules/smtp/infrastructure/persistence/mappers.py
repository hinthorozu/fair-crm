from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.value_objects import SmtpEncryptionType
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel
from app.shared.secret_encryption import decrypt_secret, encrypt_secret


def model_to_entity(model: SmtpAccountModel) -> SmtpAccount:
    return SmtpAccount(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        from_email=model.from_email,
        from_name=model.from_name,
        host=model.host,
        port=model.port,
        username=model.username,
        password=decrypt_secret(model.password),
        encryption_type=SmtpEncryptionType(model.encryption_type),
        is_default=model.is_default,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(account: SmtpAccount) -> SmtpAccountModel:
    return SmtpAccountModel(
        id=account.id,
        organization_id=account.organization_id,
        name=account.name,
        from_email=account.from_email,
        from_name=account.from_name,
        host=account.host,
        port=account.port,
        username=account.username,
        password=encrypt_secret(account.password),
        encryption_type=account.encryption_type.value,
        is_default=account.is_default,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        deleted_at=account.deleted_at,
    )


def update_model_from_entity(model: SmtpAccountModel, account: SmtpAccount) -> None:
    model.name = account.name
    model.from_email = account.from_email
    model.from_name = account.from_name
    model.host = account.host
    model.port = account.port
    model.username = account.username
    model.password = encrypt_secret(account.password)
    model.encryption_type = account.encryption_type.value
    model.is_default = account.is_default
    model.is_active = account.is_active
    model.updated_at = account.updated_at
    model.deleted_at = account.deleted_at
