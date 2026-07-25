class EmailAccountNotFoundError(Exception):
    pass


class EmailAccountAlreadyDeletedError(Exception):
    pass


class EmailAccountNotDefaultEligibleError(Exception):
    pass


class UnsupportedEmailAccountTypeError(Exception):
    pass
