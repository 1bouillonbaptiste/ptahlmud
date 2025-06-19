from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ptahlmud.backtesting.models.barriers import BarrierLevels
from ptahlmud.backtesting.models.candle_collection import CandleCollection
from ptahlmud.backtesting.position import Position, Trade
from ptahlmud.types.candle import Candle
from ptahlmud.types.signal import Side


@dataclass(slots=True)
class ExitMode:
    """Define the exit mode of a position.

    In trading systems, positions are closed and converted into trades when they reach target or with manual closing.
    An exit mode determines both when and at what price a position should be closed.

    Exit mode can represent:
    1. Take profit scenarios (when price reaches the higher barrier)
    2. Stop loss scenarios (when the price reaches the lower barrier)
    3. Time-based closes (at candle close time)
    4. Hold instructions (maintain the position)

    This class combines two information:
    * price information - which price to use for exiting the market
    * time information - at which time the position must be closed.

    """

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


def _get_position_exit_mode(position: Position, candle: Candle) -> ExitMode:
    """Check if a candle reaches position to take profit or stop loss."""
    price_reach_tp = candle.high >= position.higher_barrier
    price_reach_sl = candle.low <= position.lower_barrier

    if price_reach_tp and price_reach_sl:  # candle's price range is very wide, check which bound was reached first
        if (candle.high_time is not None) and (candle.low_time is not None):
            if candle.high_time < candle.low_time:  # price reached high before low
                return ExitMode(price_signal="high_barrier", date_signal="high")
            else:  # price reached low before high
                return ExitMode(price_signal="low_barrier", date_signal="low")
        else:  # we don't have granularity, assume close price is close enough to real sell price
            return ExitMode(price_signal="close", date_signal="close")
    elif price_reach_tp:
        return ExitMode(
            price_signal="high_barrier",
            date_signal="high" if candle.high_time else "close",
        )
    elif price_reach_sl:
        return ExitMode(
            price_signal="low_barrier",
            date_signal="low" if candle.low_time else "close",
        )

    return ExitMode(price_signal="hold", date_signal="hold")


def _close_position(position: Position, candles: CandleCollection) -> Trade:
    """Simulate the trade resulting from the position and market data.

    The position is monitored candle by candle until:
    1. A barrier (take profit/stop loss) is hit, OR
    2. The market data ends (forced close at the last available price)

    Args:
        position: the open position to simulate
        candles: market data

    Returns:
        the closed position as a new `Trade` instance

    Raises:
        ValueError: if the position opens after all available market data
    """
    candles_subset = candles.subset(from_date=position.open_date)

    if candles_subset.size == 0:
        raise ValueError(
            f"Position opened at {position.open_date} but market data ends before that date. "
            f"Latest available data: {candles_subset.candles[-1].close_time}"
        )

    for candle in candles_subset.candles:
        signal = _get_position_exit_mode(position=position, candle=candle)

        if not signal.hold_position:
            close_price, close_date = signal.to_price_date(position=position, candle=candle)
            return position.close(close_date=close_date, close_price=close_price)

    last_candle = candles_subset.candles[-1]
    return position.close(
        close_date=last_candle.close_time,
        close_price=Decimal(str(last_candle.close)),
    )


def calculate_trade(
    open_at: datetime,
    money_to_invest: Decimal,
    candles: CandleCollection,
    target: BarrierLevels,
    side: Side,
) -> Trade:
    """Calculate a trade."""
    candle = candles.get_candle_at(open_at)
    if open_at > candle.open_time:
        open_date = candle.close_time
        open_price = candle.close
    else:
        open_date = candle.open_time
        open_price = candle.open
    position = Position.open(
        open_date=open_date,
        open_price=Decimal(str(open_price)),
        money_to_invest=money_to_invest,
        fees_pct=Decimal(str(0.001)),
        side=side,
        higher_barrier=Decimal(str(target.high_value(open_price))),
        lower_barrier=Decimal(str(target.low_value(open_price))),
    )
    return _close_position(position, candles)
