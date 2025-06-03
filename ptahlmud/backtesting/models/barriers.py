"""Define `BarrierLevels`.

A **barrier** is a limit where the asset is sold if it reaches it.
These barriers are _always_ expressed in percentage to reference price and can be converted to actual price.
"""

from pydantic import BaseModel, Field


class BarrierLevels(BaseModel):
    """Represents trading barriers.

    Attributes:
        high: higher barrier, defaults to inf (a.k.a. "never sell")
        low: lower barrier, default to 1 (a.k.a. "never sell")
    """

    high: float = Field(gt=0, lt=float("inf"))
    low: float = Field(gt=0, lt=1)

    def high_value(self, price: float) -> float:
        """Convert the higher barrier in pct to actual price value."""
        return price * (1 + self.high)

    def low_value(self, price: float) -> float:
        """Convert the lower barrier in pct to actual price value."""
        return price * (1 - self.low)
