class MailTemplateError(Exception):
    """Base error for mail template domain rules."""


class MailTemplateNotFoundError(MailTemplateError):
    pass


class MailTemplateAlreadyDeletedError(MailTemplateError):
    pass


class MailTemplateKeyAlreadyExistsError(MailTemplateError):
    pass


class MailTemplateDefaultAlreadyExistsError(MailTemplateError):
    pass


class InvalidMailTemplateNameError(MailTemplateError):
    pass


class InvalidMailTemplateKeyError(MailTemplateError):
    pass


class InvalidMailTemplateSubjectError(MailTemplateError):
    pass


class InvalidMailTemplateTypeError(MailTemplateError):
    pass


class InvalidMailTemplateLanguageError(MailTemplateError):
    pass


class MailTemplateNotDefaultEligibleError(MailTemplateError):
    pass


class MailTemplateRenderError(MailTemplateError):
    pass


class MailTemplateInactiveForTestError(MailTemplateError):
    pass


class MailTemplateDefaultSmtpNotFoundError(MailTemplateError):
    pass


class InvalidMailTemplateTestRecipientError(MailTemplateError):
    pass


class InvalidMailTemplateTestSubjectError(MailTemplateError):
    pass
