from pathlib import Path


RETRY_OPERATION = Path("app/modules/operations/application/retry_operation.py")


def test_scraper_retry_uses_scraper_execute_permission():
    source = RETRY_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_SCRAPER_EXECUTE = "fair_crm.scraper.execute"' in source
    assert "or operation.operation_type == OperationType.SCRAPER" in source
    assert "PERMISSION_SCRAPER_EXECUTE" in source
    assert "permission_code=permission_code" in source


def test_retry_keeps_existing_business_special_cases_and_generic_fallback():
    source = RETRY_OPERATION.read_text(encoding="utf-8")

    assert 'PERMISSION_EXECUTE = "fair_crm.operations.execute"' in source
    assert 'PERMISSION_BULK_EMAIL_EXECUTE = "fair_crm.fair_emails.execute"' in source
    assert "if operation.operation_type == OperationType.BULK_EMAIL" in source
    assert "if operation.operation_type == OperationType.ENRICHMENT" in source
    assert "else PERMISSION_EXECUTE" in source
