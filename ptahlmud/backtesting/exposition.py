import datetime
import enum
from dataclasses import dataclass


class Side(str, enum.Enum):
    LONG = "LONG"


@dataclass
class Position:
    """Represent a position on the market.

    A position is the expression of a market commitment, or exposure, held by a trader.
    When the position is closed, it becomes a trade.

    Attributes:
        side: the side of the position
        volume: volume of coin
        open_price: price of the coin when the position was open
        open_date: the date when the position was open
        initial_investment: the initial amount of currency the trader invested
        fees_pct: cost in percentage of opening the position
        stop_loss: close the position (stop your losses) if price drops too low
        take_profit: close the position (take your profits) if price reaches your target
    """

    side: Side

    volume: float
    open_price: float
    open_date: datetime.datetime
    initial_investment: float
    fees_pct: float

    stop_loss: float
    take_profit: float

    @property
    def open_fees(self) -> float:
        return _calculate_fees(investment=self.initial_investment, fees_pct=self.fees_pct)

    @property
    def is_closed(self) -> bool:
        """A position is always open."""
        return False


@dataclass
class Trade(Position):
    """Represent a trade.

    A Trade is-a position that has been closed.

    Attributes:
        close_date: the date when a position was closed, could be any time
        close_price: price of the coin when the position was closed
    """

    close_date: datetime.datetime
    close_price: float

    @property
    def receipt(self) -> float:
        return self.volume * self.close_price

    @property
    def close_fees(self) -> float:
        return _calculate_fees(investment=self.receipt, fees_pct=self.fees_pct)

    @property
    def total_profit(self) -> float:
        """Overall profit of the trade."""
        return self.receipt - self.initial_investment - self.close_fees

    @property
    def total_fees(self) -> float:
        """Overall cost of the trade."""
        return self.open_fees + self.close_fees

    @property
    def total_duration(self) -> datetime.timedelta:
        """Overall duration of the trade."""
        return self.close_date - self.open_date

    @property
    def is_closed(self) -> bool:
        """A trade is always closed."""
        return True

    @property
    def reached_take_profit(self) -> bool:
        """Whether the trade reached the take profit."""
        return self.close_price >= self.take_profit

    @property
    def reached_stop_loss(self) -> bool:
        """Whether the trade reached the stop loss."""
        return self.close_price <= self.stop_loss


def _calculate_fees(investment: float, fees_pct: float) -> float:
    """The cost to open a position."""
    return investment * fees_pct


def open_position(
    open_date: datetime.datetime,
    open_price: float,
    money_to_invest: float,
    fees_pct: float,
    stop_loss: float = 0,
    take_profit: float = float("inf"),
) -> Position:
    """Opens a new trading position.

    This function is the preferred way to create a new instance of a trading position.

    Parameters:
        open_date: the date and time when the position is to be opened
        open_price: the price at which the position is opened
        money_to_invest: the amount of money to be invested in the position
        fees_pct: cost in percentage applied by a broker
        stop_loss: the price level at which the position should be automatically closed to limit losses
        take_profit: the price level at which the position should be automatically closed to secure profits

    Returns:
        a new instance of position
    """
    open_fees = _calculate_fees(money_to_invest, fees_pct=fees_pct)
    volume = (money_to_invest - open_fees) / open_price
    return Position(
        open_date=open_date,
        open_price=open_price,
        volume=volume,
        initial_investment=money_to_invest,
        fees_pct=fees_pct,
        stop_loss=stop_loss,
        take_profit=take_profit,
        side=Side.LONG,
    )


def close_position(position: Position, close_date: datetime.datetime, close_price: float) -> Trade:
    """Close a position to a trade.

    Args:
        position: the position to be closed
        close_date: time when the position is closed
        close_price: price when the position is closed

    Returns:
        closed position as a new trade instance

    Raises:
        ValueError: if the position is already a trade, since it is inheriting
    """
    if position.is_closed:
        raise ValueError("Position il already closed.")

    return Trade(
        **vars(position),
        close_date=close_date,
        close_price=close_price,
    )
