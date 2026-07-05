class MailSendOperationError(Exception):
    """Base error for mail send operation domain rules."""


class MissingOrganizationIdError(MailSendOperationError):
    pass


class MailSendOperationNotFoundError(MailSendOperationError):
    pass


class InvalidMailSendOperationTransitionError(MailSendOperationError):
    pass


class MailSendOperationRetryNotSupportedError(MailSendOperationError):
    pass
