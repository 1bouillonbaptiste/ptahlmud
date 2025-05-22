import datetime
import enum
from dataclasses import dataclass

__FEES_PCT = 0.001


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
        open_fees: cost of opening the position, fees are being taken before calculating position volume
        stop_loss: close the position (stop your losses) if price drops too low
        take_profit: close the position (take your profits) if price reaches your target
    """

    side: Side

    volume: float
    open_price: float
    open_date: datetime.datetime
    initial_investment: float
    open_fees: float

    stop_loss: float
    take_profit: float


@dataclass
class Trade(Position):
    """Represent a trade.

    A Trade is-a position that has been closed.

    Attributes:
        close_date: the date when a position was closed, could be any time
        close_price: price of the coin when the position was closed
        close_fees: fees from selling the position
    """

    close_date: datetime.datetime
    close_price: float
    close_fees: float


def _calculate_open_fees(investment: float) -> float:
    """The cost to open a position."""
    return investment * __FEES_PCT


def open_position(
    open_date: datetime.datetime,
    open_price: float,
    money_to_invest: float,
    stop_loss: float = 0,
    take_profit: float = float("inf"),
) -> Position:
    """Opens a new trading position.

    This function is the preferred way to create a new instance of a trading position.

    Parameters:
        open_date: the date and time when the position is to be opened
        open_price: the price at which the position is opened
        money_to_invest: the amount of money to be invested in the position
        stop_loss: the price level at which the position should be automatically closed to limit losses
        take_profit: the price level at which the position should be automatically closed to secure profits

    Returns:
        a new instance of position
    """
    open_fees = _calculate_open_fees(money_to_invest)
    volume = (money_to_invest - open_fees) / open_price
    return Position(
        open_date=open_date,
        open_price=open_price,
        volume=volume,
        open_fees=open_fees,
        initial_investment=money_to_invest,
        stop_loss=stop_loss,
        take_profit=take_profit,
        side=Side.LONG,
    )
