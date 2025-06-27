"""Define a custom operation applied during fluctuations conversion."""

from typing import Callable, TypeAlias

import pandas as pd
from pydantic import BaseModel

PandasOperation: TypeAlias = Callable[[pd.Series | pd.DataFrame], int | float]


class CustomOperation(BaseModel):
    """Define a custom operation to be applied to a dataframe.

    Attributes:
        column: name to give to the new column
        function: operation to apply on the dataframe column
        requires: dataframe column(s) on which to apply the operation.
    """

    column: str
    function: PandasOperation
    requires: str | list[str]


_OPERATIONS_REGISTRY: dict[str, CustomOperation] = {}


def register_operation(custom_operation: CustomOperation) -> None:
    """Register a custom operation."""
    _OPERATIONS_REGISTRY[custom_operation.column] = custom_operation


def get_operation(column: str) -> CustomOperation:
    """Get the registered function."""
    if column not in _OPERATIONS_REGISTRY:
        raise ValueError(f"Unknown custom operation '{column}'.")
    return _OPERATIONS_REGISTRY[column]
