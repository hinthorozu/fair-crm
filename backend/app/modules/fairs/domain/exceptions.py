class FairDomainError(Exception):
    """Base fair domain error."""


class FairNotFoundError(FairDomainError):
    pass


class FairAlreadyArchivedError(FairDomainError):
    pass


class FairNotArchivedError(FairDomainError):
    pass


class InvalidFairNameError(FairDomainError):
    pass


class InvalidFairDateRangeError(FairDomainError):
    pass


class InvalidFairAdapterConfigError(FairDomainError):
    pass


class FairScraperNotConfiguredError(FairDomainError):
    pass


class FairScraperAdapterNotConfiguredError(FairScraperNotConfiguredError):
    pass


class FairScraperUrlNotConfiguredError(FairScraperNotConfiguredError):
    pass


class InvalidFairSourceUrlError(FairDomainError):
    pass


class InvalidFairWebsiteError(FairDomainError):
    pass


class FairEnrichmentNoCandidatesError(FairDomainError):
    pass


class TobbCalendarReadError(FairDomainError):
    pass


class SystemFairMergeBlockedError(FairDomainError):
    def __init__(self, conflicts: list[dict[str, str]]) -> None:
        self.conflicts = conflicts
        super().__init__("System fair merge is blocked")


class SystemFairAlreadyMergedError(FairDomainError):
    pass
