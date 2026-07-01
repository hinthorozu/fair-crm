class ImportBatchNotFoundError(Exception):
    pass


class ImportRowNotFoundError(Exception):
    pass


class InvalidImportFileError(Exception):
    pass


class ImportBatchAlreadyAppliedError(Exception):
    pass


class InvalidImportDecisionError(Exception):
    pass


class ImportApplyError(Exception):
    pass


class InvalidColumnMappingError(Exception):
    pass


class FairRequiredError(Exception):
    pass


class FairNotFoundError(Exception):
    pass
