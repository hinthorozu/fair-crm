"""Domain errors for managed scraper adapter records."""


class ScraperAdapterDomainError(Exception):
    pass


class AdapterNotFoundError(ScraperAdapterDomainError):
    pass


class DuplicateAdapterKeyError(ScraperAdapterDomainError):
    pass


class InvalidAdapterKeyError(ScraperAdapterDomainError):
    pass


class InvalidAdapterNameError(ScraperAdapterDomainError):
    pass


class AdapterEngineNotFoundError(ScraperAdapterDomainError):
    pass
