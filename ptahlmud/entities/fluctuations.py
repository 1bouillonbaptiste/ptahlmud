"""Define a `Fluctuations` entity.

Financial time-series are often represented as candle collections, as known as **fluctuations**.
"""

import dataclasses

from ptahlmud.types.candle import Candle
from ptahlmud.types.period import Period


@dataclasses.dataclass
class Fluctuations:
    """Represent financial fluctuations."""

    candles: list[Candle]
    period: Period

    @property
    def size(self) -> int:
        """Number of candles in the collection."""
        return len(self.candles)
