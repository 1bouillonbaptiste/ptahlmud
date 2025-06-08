"""Define the `ExitSignal` class.

In trading systems, positions are closed and converted into trades when they reach target or with manual closing.
An `ExitSignal` determines both when and at what price a position should be closed.

Exit signals can represent:
1. Take profit scenarios (when price reaches the higher barrier)
2. Stop loss scenarios (when the price reaches the lower barrier)
3. Time-based closes (at candle close time)
4. Hold instructions (maintain the position)

The signal combines price information (which price level to use) with timing information
(at which point in the candle's timeline to execute the close).

"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ptahlmud.backtesting.position import Position
from ptahlmud.types.candle import Candle


@dataclass(slots=True)
class ExitSignal:
    """Represent an exit signal."""

    price_signal: Literal["high_barrier", "low_barrier", "close", "hold"]
    date_signal: Literal["high", "low", "close", "hold"]

    @property
    def hold_position(self) -> bool:
        return (self.price_signal == "hold") or (self.date_signal == "hold")

    def to_price_date(self, position: Position, candle: Candle) -> tuple[Decimal, datetime]:
        """Convert a signal to price ad date values."""

        match self.price_signal:
            case "high_barrier":
                price = position.higher_barrier
            case "low_barrier":
                price = position.lower_barrier
            case "close":
                price = Decimal(str(candle.close))
            case "hold":
                price = Decimal(0)
        match self.date_signal:
            case "high":
                date = candle.high_time
                if date is None:
                    raise ValueError("Candle has no high time.")
            case "low":
                date = candle.low_time
                if date is None:
                    raise ValueError("Candle has no low time.")
            case "close":
                date = candle.close_time
            case "hold":
                date = datetime(1900, 1, 1)
        return price, date  # noqa: price and date are always set
