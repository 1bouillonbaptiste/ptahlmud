"""Define `Candle`.

A candle is a financial entity that represents the price variation of any asset during a period of time.
It is usually represented with open, high, low and close prices, an open and close time.
We store additional attributes like high (resp. low) time to know when the high (resp. low) price was reached.
"""

import datetime
from dataclasses import dataclass


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
        volume: total asset volume traded during the candle activity
        total_trades: number of trades during the candle activity
        high_time: time the candle reached its highest point.
        low_time: time the candle reached its lowest point.

    """

    open: float
    high: float
    low: float
    close: float

    volume: float
    total_trades: int

    open_time: datetime.datetime
    close_time: datetime.datetime

    high_time: datetime.datetime | None = None
    low_time: datetime.datetime | None = None

    def __post_init__(self):
        """Validate the candle attributes."""
        _check_positive(self.open)
        _check_positive(self.high)
        _check_positive(self.low)
        _check_positive(self.close)
        _check_positive(self.volume)
        _check_positive(self.total_trades)

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

        if self.high_time:
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
