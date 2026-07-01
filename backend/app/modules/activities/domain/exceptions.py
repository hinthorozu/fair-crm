class ActivityDomainError(Exception):
    pass


class ActivityNotFoundError(ActivityDomainError):
    pass


class CustomerNotFoundForActivityError(ActivityDomainError):
    pass


class CustomerArchivedForActivityError(ActivityDomainError):
    pass


class ContactNotFoundForActivityError(ActivityDomainError):
    pass


class ContactCustomerMismatchError(ActivityDomainError):
    pass


class InvalidActivitySubjectError(ActivityDomainError):
    pass


class InvalidActivityTypeError(ActivityDomainError):
    pass


class InvalidActivityStatusError(ActivityDomainError):
    pass


class InvalidActivitySourceError(ActivityDomainError):
    pass


class ActivityAlreadyDeletedError(ActivityDomainError):
    pass
