"""Define `Candle`.

A candle is a financial object that represents the price variation of any asset during a period of time.
It is usually represented with open, high, low and close prices, an open and close time.
We store additional attributes like high (resp. low) time to know when the high (resp. low) price was reached.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Candle:
    """Represent a candle.

    Since we instantiate potentially billions of candles, we require a lightweight object.
    We don't use pydantic model or dataclass for performance reasons, would be awesome to validate fields.
    We don't use a NamedTuple because we need to access candle's attributes frequently.

    Attributes:
        open: price the candle opened at.
        high: price the candle reached at its highest point.
        low: price the candle reached at its lowest point.
        close: price the candle closed at.
        open_time: time the candle opened.
        close_time: time the candle closed.
        high_time: time the candle reached its highest point.
        low_time: time the candle reached its lowest point.

    """

    open: float
    high: float
    low: float
    close: float

    open_time: datetime
    close_time: datetime

    high_time: datetime | None = None
    low_time: datetime | None = None

    def __post_init__(self):
        """Validate the candle attributes."""
        _check_positive(self.open)
        _check_positive(self.high)
        _check_positive(self.low)
        _check_positive(self.close)

        if self.low > self.open:
            raise ValueError("`low` price must be lower than `open` price.")
        if self.low > self.close:
            raise ValueError("`low` price must be higher than `close` price.")

        if self.high < self.open:
            raise ValueError("`high` price must be higher than `open` price.")
        if self.high < self.close:
            raise ValueError("`high` price must be lower than `close` price.")

        if self.high_time and not self.low_time:
            raise ValueError("`high_time` and `low_time` must be both set or both left empty.")

        if self.low_time and not self.high_time:
            raise ValueError("`high_time` and `low_time` must be both set or both left empty.")

        if self.high_time and self.low_time:
            if self.high_time < self.open_time:
                raise ValueError("`high_time` must be later than `open_time`.")
            if self.high_time > self.close_time:
                raise ValueError("`high_time` must be earlier than `close_time`.")

            if self.low_time < self.open_time:
                raise ValueError("`low_time` must be later than `open_time`.")
            if self.low_time > self.close_time:
                raise ValueError("`low_time` must be earlier than `close_time`.")


def _check_positive(price: float):
    """Validate a number is positive."""
    if price < 0:
        raise ValueError("Found negative number.")


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
