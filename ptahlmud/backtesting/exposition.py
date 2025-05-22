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
