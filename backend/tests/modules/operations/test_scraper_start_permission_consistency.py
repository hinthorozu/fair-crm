from pathlib import Path


CREATE_OPERATION = Path("app/modules/operations/application/create_operation.py")
START_OPERATION = Path("app/modules/operations/application/start_operation.py")


def test_immediate_scraper_create_uses_scraper_execute_permission():
    source = CREATE_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_SCRAPER_EXECUTE = "fair_crm.scraper.execute"' in source
    assert 'if command.operation_type == "scraper" and command.start_immediately' in source
    assert "PERMISSION_SCRAPER_EXECUTE" in source
    assert "else PERMISSION_CREATE" in source


def test_scraper_start_uses_scraper_execute_permission():
    source = START_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_SCRAPER_EXECUTE = "fair_crm.scraper.execute"' in source
    assert "if operation.operation_type == OperationType.SCRAPER" in source
    assert "PERMISSION_SCRAPER_EXECUTE" in source
    assert "else PERMISSION_EXECUTE" in source


def test_existing_special_cases_remain_available():
    create_source = CREATE_OPERATION.read_text(encoding="utf-8")
    start_source = START_OPERATION.read_text(encoding="utf-8")

    assert 'command.operation_type == "bulk_email" and command.start_immediately' in create_source
    assert 'command.operation_type == "duplicate_check" and command.start_immediately' in create_source
    assert 'command.operation_type == "enrichment" and command.start_immediately' in create_source
    assert "operation.operation_type == OperationType.BULK_EMAIL" in start_source
    assert "operation.operation_type == OperationType.ENRICHMENT" in start_source
