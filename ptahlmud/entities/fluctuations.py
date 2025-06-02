"""Define a `Fluctuations` entity.

Financial time-series are often represented as candle collections, as known as **fluctuations**.
"""

import dataclasses
from datetime import datetime

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

    def get_candle_at(self, date: datetime) -> Candle:
        """Return the candle containing `date`."""
        index = _get_lower_bound_index(date=date, candles=self.candles)
        return self.candles[index]

    def subset(self, from_date: datetime | None = None, to_date: datetime | None = None) -> "Fluctuations":
        """Return a subset of object candles."""
        if (from_date is None) and (to_date is None):
            return self
        if from_date is None:
            from_date = self.candles[0].open_time
        if to_date is None:
            to_date = self.candles[-1].close_time
        from_index = _get_lower_bound_index(date=from_date, candles=self.candles)
        to_index = _get_lower_bound_index(date=to_date, candles=self.candles) + 1
        candles = self.candles[from_index:to_index]
        if candles and (candles[-1].open_time == to_date):
            candles.pop()
        return Fluctuations(
            candles=candles,
            period=self.period,
        )


def _get_lower_bound_index(date: datetime, candles: list[Candle]) -> int:
    """Find the index of the candle containing `date`."""
    if not candles:
        raise ValueError("No candles provided.")

    if date < candles[0].open_time:
        return 0
    if date >= candles[-1].close_time:
        return len(candles)

    if len(candles) == 1:
        return 0

    middle_index = len(candles) // 2
    if date < candles[middle_index].open_time:
        return _get_lower_bound_index(date=date, candles=candles[:middle_index])
    return middle_index + _get_lower_bound_index(date=date, candles=candles[middle_index:])
