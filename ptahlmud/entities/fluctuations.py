"""Define a `Fluctuations` entity.

Financial time-series are often represented as candle collections, as known as **fluctuations**.
"""

from pydantic import BaseModel, ConfigDict

from ptahlmud.types.candle import Candle
from ptahlmud.types.period import Period


class Fluctuations(BaseModel):
    """Represent financial fluctuations."""

    config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    candles: list[Candle]
    period: Period

    @property
    def size(self) -> int:
        """Number of candles in the collection."""
        return len(self.candles)
