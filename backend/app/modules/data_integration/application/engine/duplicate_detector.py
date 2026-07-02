from app.modules.imports.domain.services.duplicate_detector import find_customer_match


class DuplicateDetector:
    find_customer_match = staticmethod(find_customer_match)
