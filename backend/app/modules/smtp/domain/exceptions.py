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
