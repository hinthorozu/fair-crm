class ContactDomainError(Exception):
    pass


class ContactNotFoundError(ContactDomainError):
    pass


class CustomerNotFoundForContactError(ContactDomainError):
    pass


class CustomerArchivedForContactError(ContactDomainError):
    pass


class InvalidContactNameError(ContactDomainError):
    pass


class InvalidContactEmailError(ContactDomainError):
    pass


class ContactAlreadyDeletedError(ContactDomainError):
    pass
