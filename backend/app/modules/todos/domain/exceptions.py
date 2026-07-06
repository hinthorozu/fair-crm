class TodoDomainError(Exception):
    pass


class TodoNotFoundError(TodoDomainError):
    pass


class InvalidTodoTitleError(TodoDomainError):
    pass


class InvalidTodoStatusError(TodoDomainError):
    pass


class InvalidTodoPriorityError(TodoDomainError):
    pass


class InvalidTodoCategoryError(TodoDomainError):
    pass


class InvalidTodoStatusTransitionError(TodoDomainError):
    pass


class InvalidWorklistPrimaryStatusError(TodoDomainError):
    pass


class InvalidOutcomeCodeError(TodoDomainError):
    pass


class InvalidOutcomeNameError(TodoDomainError):
    pass


class InvalidOutcomePrimaryWorklistStatusError(TodoDomainError):
    pass


class TodoOutcomeDefinitionNotFoundError(TodoDomainError):
    pass


class DuplicateOutcomeCodeError(TodoDomainError):
    pass


class OutcomeCodeImmutableError(TodoDomainError):
    pass


class TodoWorklistStateNotFoundError(TodoDomainError):
    pass


class TodoSourceFairChangeNotAllowedError(TodoDomainError):
    pass


class TodoMissingSourceFairError(TodoDomainError):
    pass


class WorklistCustomerNotInTodoError(TodoDomainError):
    pass


class TodoOutcomeInactiveError(TodoDomainError):
    pass


class InvalidWorklistNoteError(TodoDomainError):
    pass
