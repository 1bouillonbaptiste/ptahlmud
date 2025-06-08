"""Define trading entities for backtesting.

This module contains the `Position` and `Trade` classes, which are essential
components for simulating trades in a backtesting environment.

- A `Position` represents the active market exposure held by a trader, with attributes
  such as open price, barriers for take profit or stop loss, and the initial amount invested.
- A `Trade` extends `Position` and represents a completed trade, including the closing
  information (e.g., closing date, closing price, fees, and profit).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from ptahlmud.types.signal import Side


def _calculate_fees(investment: Decimal, fees_pct: Decimal) -> Decimal:
    """The cost to open a position."""
    return investment * fees_pct


@dataclass
class Position:
    """Represent an open position.

    A `Position` is the expression of a trader's market commitment. It contains details about
    the side (LONG/SHORT), investment size, barriers for exit, and associated fees. When the
    position is closed, it converts into a `Trade`.

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

    volume: Decimal
    open_price: Decimal
    open_date: datetime
    initial_investment: Decimal
    fees_pct: Decimal

    lower_barrier: Decimal
    higher_barrier: Decimal

    @property
    def open_fees(self) -> Decimal:
        """Fees incurred at the moment of opening the position."""
        return _calculate_fees(investment=self.initial_investment, fees_pct=self.fees_pct)

    @property
    def is_closed(self) -> bool:
        """A position is always open."""
        return False

    @classmethod
    def open(
        cls,
        open_date: datetime,
        open_price: Decimal,
        money_to_invest: Decimal,
        fees_pct: Decimal,
        side: Side,
        lower_barrier: Decimal | None = None,
        higher_barrier: Decimal | None = None,
    ):
        """Open a trading position."""
        lower_barrier = lower_barrier or Decimal("0")
        higher_barrier = higher_barrier or Decimal(float("inf"))
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

    def close(self, close_date: datetime, close_price: Decimal) -> "Trade":
        """Close an open position and convert it to a `Trade`."""
        if self.is_closed:
            raise ValueError("Position il already closed.")
        return Trade(
            **vars(self),
            close_date=close_date,
            close_price=close_price,
        )


@dataclass
class Trade(Position):
    """Represent a completed trade.

    A `Trade` is an extension of a `Position` that has been closed. It includes
    details about when and at what price the trade was completed, as well as
    calculated financial metrics such as profit and fees.

    Attributes:
        close_date: the date when a position was closed, could be any time
        close_price: price of the coin when the position was closed
    """

    close_date: datetime
    close_price: Decimal

    @property
    def receipt(self) -> Decimal:
        """The amount of money received after closing the trade."""
        if self.side == Side.LONG:
            price_diff = self.close_price - self.open_price
        else:
            price_diff = self.open_price - self.close_price

        return self.volume * price_diff + self.initial_investment - self.open_fees

    @classmethod
    def open(cls, *args, **kwargs) -> None:
        """Prevent opening trades directly.

        A `Trade` _must_ be created by closing a `Position`.
        """

        raise RuntimeError("Cannot open a trade, please use `Position.open()` instead.")

    @property
    def close_fees(self) -> Decimal:
        """Fees incurred at the moment of closing the trade."""

        return _calculate_fees(investment=self.receipt, fees_pct=self.fees_pct)

    @property
    def total_profit(self) -> Decimal:
        """The overall profit or loss from the trade."""
        return self.receipt - self.initial_investment - self.close_fees

    @property
    def total_fees(self) -> Decimal:
        """The total fees incurred during the trade."""
        return self.open_fees + self.close_fees

    @property
    def total_duration(self) -> timedelta:
        """The duration for which the trade remained open."""
        return self.close_date - self.open_date

    @property
    def is_closed(self) -> bool:
        """A trade is always a closed position."""
        return True
