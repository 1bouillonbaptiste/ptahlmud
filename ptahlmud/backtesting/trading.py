from dataclasses import dataclass
from datetime import datetime, timedelta

from ptahlmud.types.signal import Side


def _calculate_fees(investment: float, fees_pct: float) -> float:
    """The cost to open a position."""
    return investment * fees_pct


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
        lower_barrier: close the position if price reaches this barrier
        higher_barrier: close the position if the price reaches this barrier
    """

    side: Side

    volume: float
    open_price: float
    open_date: datetime
    initial_investment: float
    fees_pct: float

    lower_barrier: float
    higher_barrier: float

    @property
    def open_fees(self) -> float:
        return _calculate_fees(investment=self.initial_investment, fees_pct=self.fees_pct)

    @property
    def is_closed(self) -> bool:
        """A position is always open."""
        return False

    @classmethod
    def open(
        cls,
        open_date: datetime,
        open_price: float,
        money_to_invest: float,
        fees_pct: float,
        side: Side,
        lower_barrier: float = 0,
        higher_barrier: float = float("inf"),
    ):
        """Open a trading position."""
        open_fees = _calculate_fees(money_to_invest, fees_pct=fees_pct)
        volume = (money_to_invest - open_fees) / open_price
        return cls(
            open_date=open_date,
            open_price=open_price,
            volume=volume,
            initial_investment=money_to_invest,
            fees_pct=fees_pct,
            side=side,
            lower_barrier=lower_barrier,
            higher_barrier=higher_barrier,
        )

    def close(self, close_date: datetime, close_price: float) -> "Trade":
        """Close the trading position."""
        if self.is_closed:
            raise ValueError("Position il already closed.")
        return Trade(
            **vars(self),
            close_date=close_date,
            close_price=close_price,
        )


@dataclass
class Trade(Position):
    """Represent a trade.

    A Trade is-a position that has been closed.

    Attributes:
        close_date: the date when a position was closed, could be any time
        close_price: price of the coin when the position was closed
    """

    close_date: datetime
    close_price: float

    @property
    def receipt(self) -> float:
        """The amount of money received after closing the trade."""
        if self.side == Side.LONG:
            price_diff = self.close_price - self.open_price
        else:
            price_diff = self.open_price - self.close_price

        return self.volume * price_diff + self.initial_investment - self.open_fees

    @classmethod
    def open(cls, *args, **kwargs) -> None:
        """Cannot open a trade."""
        raise RuntimeError("Cannot open a trade, please use `Position.open()` instead.")

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
    def total_duration(self) -> timedelta:
        """Overall duration of the trade."""
        return self.close_date - self.open_date

    @property
    def is_closed(self) -> bool:
        """A trade is always closed."""
        return True
