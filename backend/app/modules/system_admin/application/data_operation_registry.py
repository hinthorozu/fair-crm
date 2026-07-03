from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class DataOperationDefinition:
    key: str
    name: str
    description: str
    result_mode: Literal["file", "dataset"] = "file"
    script_path: str | None = None
    dataset_kind: str | None = None
    destructive: bool = False
    output_mode: Literal["excel", "directory", "none", "dataset"] = "excel"


DATA_OPERATIONS: tuple[DataOperationDefinition, ...] = (
    DataOperationDefinition(
        key="analyze_customers_without_fair",
        name="Analyze Customers Without Fair",
        description=(
            "First step of the customer cleanup workflow. "
            "Analyzes customers with no fair participation and opens an interactive result table. "
            "Read-only; does not modify the database."
        ),
        result_mode="dataset",
        dataset_kind="customers_without_fair",
        output_mode="dataset",
    ),
    DataOperationDefinition(
        key="duplicate_customer_analysis",
        name="Duplicate Customer Analysis",
        description=(
            "Group customers by a field you choose (company name, email, website, or phone) and review "
            "groups with two or more customers. Read-only; does not modify the database."
        ),
        result_mode="dataset",
        dataset_kind="duplicate_customer_groups",
        output_mode="dataset",
    ),
)


DATA_OPERATIONS_BY_KEY = {operation.key: operation for operation in DATA_OPERATIONS}


def get_operation_definition(operation_key: str) -> DataOperationDefinition | None:
    return DATA_OPERATIONS_BY_KEY.get(operation_key)
