from pathlib import Path


CREATE_OPERATION = Path("app/modules/operations/application/create_operation.py")
START_OPERATION = Path("app/modules/operations/application/start_operation.py")
SEND_BULK_EMAIL = Path("app/modules/fair_emails/application/send_bulk_email_operation.py")


def test_immediate_bulk_email_create_uses_fair_email_execute_permission():
    source = CREATE_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_CREATE = "fair_crm.operations.create"' in source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in source
    assert 'if command.operation_type == "bulk_email" and command.start_immediately' in source
    assert "else PERMISSION_CREATE" in source
    assert "permission_code=permission_code" in source


def test_bulk_email_start_uses_fair_email_execute_but_other_starts_keep_operations_execute():
    source = START_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in source
    assert "if operation.operation_type == OperationType.BULK_EMAIL" in source
    assert "else PERMISSION_EXECUTE" in source
    assert "permission_code=permission_code" in source


def test_bulk_email_send_use_case_uses_same_canonical_permission():
    source = SEND_BULK_EMAIL.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.fair_emails.execute"' in source
    assert "permission_code=PERMISSION_EXECUTE" in source
