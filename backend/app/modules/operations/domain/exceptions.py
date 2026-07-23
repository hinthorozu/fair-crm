class OperationError(Exception):
    """Base domain error for Operation Engine."""


class OperationNotFoundError(OperationError):
    pass


class OperationRunNotFoundError(OperationError):
    pass


class OperationRunItemNotFoundError(OperationError):
    pass


class InvalidOperationTypeError(OperationError):
    pass


class InvalidOperationStatusError(OperationError):
    pass


class InvalidOperationStatusTransitionError(OperationError):
    pass


class InvalidRunStatusError(OperationError):
    pass


class InvalidRunStatusTransitionError(OperationError):
    pass


class InvalidRunItemStatusError(OperationError):
    pass


class InvalidSourceKindError(OperationError):
    pass


class InvalidOperationTitleError(OperationError):
    pass


class InvalidOperationConfigError(OperationError):
    pass


class HandlerNotRegisteredError(OperationError):
    pass


class HandlerCapabilityNotSupportedError(OperationError):
    pass


class InvalidManualTaskStatusError(OperationError):
    pass
