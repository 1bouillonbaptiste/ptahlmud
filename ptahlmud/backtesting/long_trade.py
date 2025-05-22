from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ptahlmud.backtesting.exposition import Position, Trade, close_position, open_position
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.candle import Candle


@dataclass(slots=True)
class ExitSignal:
    """How a Position needs to be closed.

    The signal can be:
    - take profit at high time
    - take profit at undefined time (take close time)
    - stop loss at low time
    - stop loss at undefined time (take close time)
    - close at close time
    """

    price_signal: Literal["take_profit", "stop_loss", "close", "hold"]
    date_signal: Literal["high", "low", "close", "hold"]

    @property
    def hold_position(self) -> bool:
        return (self.price_signal == "hold") or (self.date_signal == "hold")

    def to_price_date(self, position: Position, candle: Candle) -> tuple[float, datetime]:
        """Convert a signal to price ad date values."""

        match self.price_signal:
            case "take_profit":
                price = position.take_profit
            case "stop_loss":
                price = position.stop_loss
            case "close":
                price = candle.close
            case "hold":
                price = 0
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
        return price, date


def _get_position_exit_signal(position: Position, candle: Candle) -> ExitSignal:
    """Check if a candle reaches position to take profit or stop loss."""
    price_reach_tp = candle.high >= position.take_profit
    price_reach_sl = candle.low <= position.stop_loss

    if price_reach_tp and price_reach_sl:  # candle's price range is very wide, check which bound was reached first
        if (candle.high_time is not None) and (candle.low_time is not None):
            if candle.high_time < candle.low_time:  # price reached high before low
                return ExitSignal(price_signal="take_profit", date_signal="high")
            else:  # price reached low before high
                return ExitSignal(price_signal="stop_loss", date_signal="low")
        else:  # we don't have granularity, assume close price is close enough to real sell price
            return ExitSignal(price_signal="close", date_signal="close")
    elif price_reach_tp:
        return ExitSignal(
            price_signal="take_profit",
            date_signal="high" if candle.high_time else "close",
        )
    elif price_reach_sl:
        return ExitSignal(
            price_signal="stop_loss",
            date_signal="low" if candle.low_time else "close",
        )

    return ExitSignal(price_signal="hold", date_signal="hold")


def _enter_long_position(candle: Candle, take_profit_pct: float, stop_loss_pct: float) -> Position:
    """Enter a long position at the end of the candle."""
    return open_position(
        open_date=candle.close_time,
        open_price=candle.close,
        money_to_invest=100,
        fees_pct=0.001,
        take_profit=candle.close * (1 + take_profit_pct),
        stop_loss=candle.close * (1 - stop_loss_pct),
    )


def _get_lower_bound_index(date: datetime, candles: list[Candle]) -> int:
    """Find the index of the candle when the date starts."""

    if not candles:
        raise ValueError("No candles provided.")

    if date < candles[0].open_time:
        return 0
    if date > candles[-1].close_time:
        return len(candles)

    if len(candles) == 1:
        return 0
    middle_index = len(candles) // 2
    if date < candles[middle_index].open_time:
        return _get_lower_bound_index(date=date, candles=candles[:middle_index])
    return middle_index + _get_lower_bound_index(date=date, candles=candles[middle_index:])


def _close_long_position(position: Position, fluctuations: Fluctuations) -> Trade | None:
    """Calculate the trade resulting from the position."""
    starting_index = _get_lower_bound_index(date=position.open_date, candles=fluctuations.candles)
    if starting_index >= fluctuations.size:
        return None
    for candle in fluctuations.candles[starting_index:]:
        signal = _get_position_exit_signal(position=position, candle=candle)
        if signal.hold_position:
            continue

        close_price, close_date = signal.to_price_date(position=position, candle=candle)
        return close_position(
            position=position,
            close_date=close_date,
            close_price=close_price,
        )
    return None


def calculate_long_trade(
    candle: Candle,
    fluctuations: Fluctuations,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> Trade | None:
    """Calculate a long trade opened at a candle."""
    position = _enter_long_position(candle, take_profit_pct, stop_loss_pct)
    return _close_long_position(position, fluctuations)
