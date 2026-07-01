class ParticipationNotFoundError(Exception):
    pass


class ParticipationAlreadyDeletedError(Exception):
    pass


class DuplicateParticipationError(Exception):
    pass


class CustomerNotFoundForParticipationError(Exception):
    pass


class CustomerArchivedForParticipationError(Exception):
    pass


class FairNotFoundForParticipationError(Exception):
    pass


class FairArchivedForParticipationError(Exception):
    pass


class ContactNotFoundForParticipationError(Exception):
    pass


class ContactCustomerMismatchForParticipationError(Exception):
    pass


class InvalidParticipationStatusError(Exception):
    pass
