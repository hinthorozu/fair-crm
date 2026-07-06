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
