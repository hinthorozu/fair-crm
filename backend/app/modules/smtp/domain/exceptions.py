class SmtpAccountError(Exception):
    """Base error for SMTP account domain rules."""


class SmtpAccountNotFoundError(SmtpAccountError):
    pass


class SmtpAccountNotDefaultEligibleError(SmtpAccountError):
    pass


class SmtpAccountAlreadyDeletedError(SmtpAccountError):
    pass


class InvalidSmtpAccountNameError(SmtpAccountError):
    pass


class InvalidSmtpAccountEmailError(SmtpAccountError):
    pass


class InvalidSmtpAccountHostError(SmtpAccountError):
    pass


class InvalidSmtpAccountPortError(SmtpAccountError):
    pass


class InvalidSmtpEncryptionTypeError(SmtpAccountError):
    pass


class SmtpMailDeliveryError(SmtpAccountError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str | None = None,
        raw_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.raw_message = raw_message


class InvalidSmtpTestRecipientError(SmtpAccountError):
    pass
