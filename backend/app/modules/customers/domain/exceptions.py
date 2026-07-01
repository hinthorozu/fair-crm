class CustomerDomainError(Exception):
    """Base customer domain error."""


class CustomerNotFoundError(CustomerDomainError):
    pass


class CustomerAlreadyArchivedError(CustomerDomainError):
    pass


class CustomerNotArchivedError(CustomerDomainError):
    pass


class InvalidCustomerNameError(CustomerDomainError):
    pass


class InvalidCustomerEmailError(CustomerDomainError):
    pass
