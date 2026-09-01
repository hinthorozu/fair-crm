from pathlib import Path


RETRY_OPERATION = Path("app/modules/operations/application/retry_operation.py")


def test_bulk_email_retry_uses_fair_email_execute_but_other_retries_keep_operations_execute():
    source = RETRY_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in source
    assert "if operation.operation_type == OperationType.BULK_EMAIL" in source
    assert "else PERMISSION_EXECUTE" in source
    assert "permission_code=permission_code" in source


def test_retry_loads_operation_before_selecting_business_permission():
    source = RETRY_OPERATION.read_text(encoding="utf-8")

    load_index = source.index("operation = self._operation_repository.get_by_id(")
    permission_index = source.index("permission_code = (")
    check_index = source.index("if not self._authorization.check_permission(")
    assert load_index < permission_index < check_index
