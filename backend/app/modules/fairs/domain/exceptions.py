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
