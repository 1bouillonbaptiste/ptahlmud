"""Define `Candle`.

A candle is a financial object that represents the price variation of any asset during a period of time.
It is usually represented with open, high, low and close prices, an open and close time.
We store additional attributes like high (resp. low) time to know when the high (resp. low) price was reached.
"""

from datetime import datetime

from ptahlmud.core.fluctuations import Candle


class CandleCollection:
    """Represent a collection of `Candle` objects."""

    def __init__(self, candles: list[Candle]):
        self.candles = candles

    @property
    def size(self) -> int:
        """Number of candles in the collection."""
        return len(self.candles)

    def first_opening_date(self) -> datetime:
        """Return the first candle's opening date."""
        return self.candles[0].open_time

    def last_closing_date(self) -> datetime:
        """Return the last candle's closing date."""
        return self.candles[-1].close_time

    def get_candle_at(self, date: datetime) -> Candle:
        """Return the candle containing `date`."""
        index = _get_lower_bound_index(date=date, candles=self.candles)
        return self.candles[index]

    def subset(self, from_date: datetime | None = None, to_date: datetime | None = None) -> "CandleCollection":
        """Retrieves candles within a specified date range, inclusive of both endpoints."""
        if (from_date is None) and (to_date is None):
            return self
        if from_date is None:
            from_date = self.first_opening_date()
        if to_date is None:
            to_date = self.last_closing_date()
        from_index = _get_lower_bound_index(date=from_date, candles=self.candles)
        to_index = _get_lower_bound_index(date=to_date, candles=self.candles) + 1
        candles = self.candles[from_index:to_index]
        if candles and (candles[-1].open_time == to_date):
            candles.pop()
        return CandleCollection(
            candles=candles,
        )

    def first_candles(self, n: int) -> "CandleCollection":
        """Return the first `n` candles as a new collection."""
        return CandleCollection(candles=self.candles[:n])


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
