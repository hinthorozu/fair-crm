class FairCrmError(Exception):
    """Base application error."""


class NotFoundError(FairCrmError):
    pass


class ValidationError(FairCrmError):
    pass


class ForbiddenError(FairCrmError):
    pass


class UnauthorizedError(FairCrmError):
    pass


class ConflictError(FairCrmError):
    pass
