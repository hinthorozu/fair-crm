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
