from pathlib import Path


CREATE_OPERATION = Path("app/modules/operations/application/create_operation.py")
START_OPERATION = Path("app/modules/operations/application/start_operation.py")


def test_immediate_enrichment_create_uses_scraper_execute_permission():
    source = CREATE_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_SCRAPER_EXECUTE = "fair_crm.scraper.execute"' in source
    assert 'if command.operation_type == "enrichment" and command.start_immediately' in source
    assert "PERMISSION_SCRAPER_EXECUTE" in source
    assert "else PERMISSION_CREATE" in source


def test_enrichment_start_uses_scraper_execute_permission():
    source = START_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_SCRAPER_EXECUTE = "fair_crm.scraper.execute"' in source
    assert "if operation.operation_type == OperationType.ENRICHMENT" in source
    assert "PERMISSION_SCRAPER_EXECUTE" in source
    assert "else PERMISSION_EXECUTE" in source


def test_existing_special_cases_and_generic_fallbacks_remain_available():
    create_source = CREATE_OPERATION.read_text(encoding="utf-8")
    start_source = START_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_CREATE = "fair_crm.operations.create"' in create_source
    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in create_source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in create_source
    assert 'command.operation_type == "bulk_email" and command.start_immediately' in create_source
    assert 'command.operation_type == "duplicate_check" and command.start_immediately' in create_source

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in start_source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in start_source
    assert "operation.operation_type == OperationType.BULK_EMAIL" in start_source
