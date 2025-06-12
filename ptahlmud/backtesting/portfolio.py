"""Define trading portfolios elements.

This module defines the `Portfolio`, `WealthItem`, and `WealthSeries` classes, which collectively
represent and manage a trading portfolio's state and its evolution over time.

Key concepts:
- `WealthItem`: Represents the portfolio's wealth at a specific time, including asset volume
  and available currency.
- `WealthSeries`: A time series of `WealthItem` instances combined with entry points to track
  wealth changes.
- `Portfolio`: A higher-level class for managing trading activities, updating portfolio
  wealth based on trades, and tracking available capital and assets.

This structure is essential for simulating dynamic portfolio behavior in trading backtests.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ptahlmud.backtesting.position import Trade


@dataclass(slots=True)
class WealthItem:
    """Represent the wealth of a portfolio at a given point in time.

    `WealthItem` combines the current amount of currency and the volume of the traded
    asset, ensuring no negative amounts can occur.

    Attributes:
        date: the timestamp the wealth data refers to
        asset: the amount of asset held in decimal form
        currency: the amount of free currency held in decimal form
    """

    date: datetime
    asset: Decimal
    currency: Decimal

    def __post_init__(self):
        if (self.asset < 0) | (self.currency < 0):
            raise ValueError("Cannot store negative amount of asset or currency.")

    def add_currency(self, amount: Decimal) -> None:
        """Update the stored currency amount by adding the given amount."""
        if self.currency + amount < 0:
            raise ValueError("Cannot store negative amount of currency.")
        self.currency += amount

    def add_asset(self, volume: Decimal) -> None:
        """Update the stored asset volume by adding the specified volume."""
        if self.asset + volume < 0:
            raise ValueError("Cannot store negative volume of asset.")
        self.asset += volume


@dataclass
class WealthSeries:
    """Store and track portfolio wealth changes over time.

    The `WealthSeries` class maintains a sequence of `WealthItem` objects to record changes
    in portfolio wealth, along with entries defining when the portfolio enters the market.

    Attributes:
        items: list of `WealthItem` instances, ordered by timestamp
        entries: list of timestamps marking market entry points
    """

    items: list[WealthItem]
    entries: list[datetime]

    def entries_after(self, date: datetime) -> bool:
        """Check if there are any entries after a given date."""
        if not self.entries:
            return False
        return date < self.entries[-1]

    def get_currency_at(self, date: datetime) -> Decimal:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return self.items[item_index].currency

    def get_asset_at(self, date: datetime) -> Decimal:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return self.items[item_index].asset

    def new_entry(self, date: datetime) -> None:
        """Create a new timed entry in the series."""
        if date < self.items[0].date:
            raise ValueError("Cannot enter the market before the initial date.")
        self.entries.insert(_find_date_position(date, self.entries), date)

    def update_wealth(self, date: datetime, currency_difference: Decimal, asset_difference: Decimal) -> None:
        """Update wealth values for the portfolio at and after the specified date."""
        before_item_index = _find_date_position(date, [item.date for item in self.items]) - 1
        before_item = self.items[before_item_index]
        new_item = WealthItem(
            date=date,
            asset=before_item.asset + asset_difference,
            currency=before_item.currency + currency_difference,
        )

        # if any following items, update them too
        for _item in self.items[before_item_index + 1 :]:
            _item.add_currency(currency_difference)
            _item.add_asset(asset_difference)
        self.items.insert(before_item_index + 1, new_item)


def _find_date_position(date: datetime, date_collection: list[datetime]) -> int:
    """Find the appropriate index to place a date in a sorted collection."""
    for index, date_i in enumerate(reversed(date_collection)):
        if date >= date_i:
            return len(date_collection) - index
    return 0


class Portfolio:
    """Represent a trading portfolio over time.

    The `Portfolio` class tracks operations involving trades and tracks
    the state of wealth (currency and asset volume) dynamically across time.
    It always starts with an asset volume of 0 and a free currency amount of 100.

    Args:
        starting_date: the initial timestamp marking the portfolio's creation
    """

    wealth_series: WealthSeries

    def __init__(self, starting_date: datetime):
        wealth_items = [
            WealthItem(
                date=starting_date,
                asset=self.default_asset_amount(),
                currency=self.default_currency_amount(),
            )
        ]
        self.wealth_series = WealthSeries(items=wealth_items, entries=[])

    @staticmethod
    def default_currency_amount() -> Decimal:
        """The amount of currency available at the start of the trading session."""
        return Decimal(100)

    @staticmethod
    def default_asset_amount() -> Decimal:
        """The amount of asset available at the start of the trading session."""
        return Decimal(0)

    def _perform_entry(self, date: datetime, currency_amount: Decimal, asset_volume: Decimal) -> None:
        """Record market entry by investing a specified amount of currency."""
        if self.wealth_series.entries_after(date):
            raise ValueError("Cannot enter the market before an existing entry.")

        if self.wealth_series.get_currency_at(date) < currency_amount:
            raise ValueError("Not enough capital to enter the market.")

        self.wealth_series.new_entry(date=date)
        self.wealth_series.update_wealth(date=date, currency_difference=-currency_amount, asset_difference=asset_volume)

    def _perform_exit(self, date: datetime, currency_amount: Decimal, asset_volume: Decimal) -> None:
        """Record market exit by selling assets."""
        if self.wealth_series.get_asset_at(date) < asset_volume:
            raise ValueError("Cannot exit the market, asset volume too small.")

        self.wealth_series.update_wealth(date=date, currency_difference=currency_amount, asset_difference=-asset_volume)

    def update_from_trade(self, trade: Trade) -> None:
        """Update the portfolio based on a completed trade."""
        self._perform_entry(trade.open_date, currency_amount=trade.initial_investment, asset_volume=trade.volume)
        self._perform_exit(
            trade.close_date, asset_volume=trade.volume, currency_amount=trade.total_profit + trade.initial_investment
        )

    def get_available_capital_at(self, date: datetime) -> Decimal:
        """Retrieve the available currency at a specific date."""
        return self.wealth_series.get_currency_at(date)

    def get_asset_volume_at(self, date: datetime) -> Decimal:
        """Retrieve the available asset volume at a specific date."""
        return self.wealth_series.get_asset_at(date)
