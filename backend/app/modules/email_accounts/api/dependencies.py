"""Email-accounts API dependencies — re-export SMTP use-case getters (adapter reuse).

Permissions: fair_crm.email_accounts.*
"""

from app.modules.smtp.api.dependencies import (  # noqa: F401
    PERMISSION_READ,
    get_audit_adapter,
    get_auth_context,
    get_authorization_adapter,
    get_create_smtp_account_use_case,
    get_delete_smtp_account_use_case,
    get_get_smtp_account_use_case,
    get_list_smtp_accounts_use_case,
    get_mail_send_operation_repository,
    get_mail_send_operation_service,
    get_send_test_smtp_mail_use_case,
    get_set_default_smtp_account_use_case,
    get_smtp_account_repository,
    get_update_smtp_account_use_case,
    require_read_permission,
)

# Stable aliases for the email-accounts surface.
get_create_email_account_use_case = get_create_smtp_account_use_case
get_update_email_account_use_case = get_update_smtp_account_use_case
get_get_email_account_use_case = get_get_smtp_account_use_case
get_list_email_accounts_use_case = get_list_smtp_accounts_use_case
get_set_default_email_account_use_case = get_set_default_smtp_account_use_case
get_delete_email_account_use_case = get_delete_smtp_account_use_case
get_send_test_email_account_mail_use_case = get_send_test_smtp_mail_use_case
get_email_account_repository = get_smtp_account_repository
