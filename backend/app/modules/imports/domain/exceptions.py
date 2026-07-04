class ImportBatchNotFoundError(Exception):
    pass


class ImportRowNotFoundError(Exception):
    pass


class InvalidImportFileError(Exception):
    pass


class InvalidCanonicalImportError(Exception):
    """Canonical import document failed schema validation."""


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


class ImportAnalyzeInProgressError(Exception):
    """Another analyze job is already running for this organization."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Bu organizasyonda devam eden bir analiz işlemi var. Lütfen tamamlanmasını bekleyin."
        )


class ImportBatchAnalyzeNotAllowedError(Exception):
    pass


class ImportBulkActionInProgressError(Exception):
    """Another bulk decision or apply job is already running for this batch."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Bu import işi için devam eden bir toplu işlem var. Lütfen tamamlanmasını bekleyin."
        )


class ImportApplyInProgressError(Exception):
    """Another apply job is already running for this batch."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Bu import işi için devam eden bir uygulama işlemi var. Lütfen tamamlanmasını bekleyin."
        )


class ImportBatchDeleteBlockedError(Exception):
    """Batch cannot be deleted while analyze or apply work is in progress."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Bu import işi üzerinde devam eden bir işlem bulunmaktadır. "
            "İşlem tamamlandıktan sonra silebilirsiniz."
        )
