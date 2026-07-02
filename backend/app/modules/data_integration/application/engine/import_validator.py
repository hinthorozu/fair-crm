from app.modules.imports.domain.services.row_validator import validate_import_row


class ImportValidator:
    validate_row = staticmethod(validate_import_row)
