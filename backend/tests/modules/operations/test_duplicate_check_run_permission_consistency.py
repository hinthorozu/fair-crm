from pathlib import Path


CREATE_OPERATION = Path("app/modules/operations/application/create_operation.py")
START_OPERATION = Path("app/modules/operations/application/start_operation.py")
RETRY_OPERATION = Path("app/modules/operations/application/retry_operation.py")
DUPLICATE_HANDLER = Path("app/modules/operations/infrastructure/handlers/duplicate_check_handler.py")
DATA_OPERATION_SERVICE = Path("app/modules/system_admin/application/data_operation_service.py")


def test_immediate_duplicate_check_create_uses_operations_execute_permission():
    source = CREATE_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_CREATE = "fair_crm.operations.create"' in source
    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in source
    assert 'if command.operation_type == "duplicate_check" and command.start_immediately' in source
    assert "else PERMISSION_CREATE" in source
    assert "permission_code=permission_code" in source


def test_duplicate_check_start_keeps_operations_execute_as_canonical_permission():
    source = START_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in source
    assert "if operation.operation_type == OperationType.BULK_EMAIL" in source
    assert "else PERMISSION_EXECUTE" in source


def test_duplicate_check_retry_keeps_operations_execute_as_canonical_permission():
    retry_source = RETRY_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in retry_source
    assert "if operation.operation_type == OperationType.BULK_EMAIL" in retry_source
    assert "else PERMISSION_EXECUTE" in retry_source
    assert "permission_code=permission_code" in retry_source


def test_duplicate_handler_reuses_operations_execute_downstream_for_start_and_retry():
    handler_source = DUPLICATE_HANDLER.read_text(encoding="utf-8")
    service_source = DATA_OPERATION_SERVICE.read_text(encoding="utf-8")

    assert handler_source.count("from_operation_start=True") == 2
    assert "from_operation_start: bool = False" in handler_source
    assert "from_operation_start=from_operation_start" in handler_source
    assert 'PERMISSION_OPERATION_EXECUTE = "fair_crm.operations.execute"' in service_source
    assert "PERMISSION_OPERATION_EXECUTE if from_operation_start else PERMISSION_RUN" in service_source
    assert 'PERMISSION_RUN = "fair_crm.admin.data_operations.execute"' in service_source
