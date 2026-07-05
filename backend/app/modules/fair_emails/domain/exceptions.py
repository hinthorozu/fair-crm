class FairEmailError(Exception):
    pass


class FairNotEligibleForBulkEmailError(FairEmailError):
    pass


class FairBulkEmailRecipientNotFoundError(FairEmailError):
    pass


class FairBulkEmailTemplateNotFoundError(FairEmailError):
    pass


class FairBulkEmailBatchNotFoundError(FairEmailError):
    pass
