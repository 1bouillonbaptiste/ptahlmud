"""Define `Portfolio`.

When trading, the money comes from a portfolio and is exchanged for a certain volume of an asset.
Each trade uses a certain amount of free capital, which grows and shrinks over time.
To know exactly the state of a portfolio over time, we register the wealth over time and update it according to trades.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ptahlmud.types.signal import Action


@dataclass(slots=True)
class WealthItem:
    """Represent the wealth of a portfolio at a given time.

    Because we manage money and volumes, we use decimals to avoid rounding errors.
    """

    date: datetime
    asset: Decimal
    currency: Decimal

    def __post_init__(self):
        if (self.asset < 0) | (self.currency < 0):
            raise ValueError("Cannot store negative amount of asset or currency.")

    def add_currency(self, amount: float) -> None:
        """Update `currency`."""
        if self.currency + Decimal(amount) < 0:
            raise ValueError("Cannot store negative amount of currency.")
        self.currency += Decimal(amount)

    def add_asset(self, volume: float) -> None:
        """Update `asset`."""
        if self.asset + Decimal(volume) < 0:
            raise ValueError("Cannot store negative volume of asset.")
        self.asset += Decimal(volume)


@dataclass(slots=True)
class TimedAction:
    """An action that occurred at a specific time."""

    date: datetime
    action: Action


@dataclass
class WealthSeries:
    """Store the wealth of a portfolio over time.

    Items and signals are always ordered by date.

    Attributes:
        items: wealth time series values
        actions: list of signals that have been applied to create the series
    """

    items: list[WealthItem]
    actions: list[TimedAction]

    def entries_after(self, date: datetime) -> bool:
        """Check if there are any entries after a given date."""
        for _action in reversed(self.actions):
            if _action.date < date:
                # since signals are ordered, the following stored signals occurred before
                return False
            if _action.action == Action.ENTER:
                return True
        return False

    def get_currency_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return float(self.items[item_index].currency)

    def get_asset_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return float(self.items[item_index].asset)

    def _new_entry(self, date: datetime) -> None:
        """Create a new timed entry in the series."""
        if date < self.items[0].date:
            raise ValueError("Cannot enter the market before the initial date.")
        new_action = TimedAction(date=date, action=Action.ENTER)
        current_dates = [action.date for action in self.actions]
        self.actions.insert(_find_date_position(date, current_dates), new_action)

    def _new_exit(self, date: datetime) -> None:
        """Create a new timed exit in the series."""
        new_action = TimedAction(date=date, action=Action.EXIT)
        current_dates = [action.date for action in self.actions]
        self.actions.insert(_find_date_position(date, current_dates), new_action)

    def _update_wealth(self, date: datetime, investment: float, volume: float) -> None:
        """Update the wealth series."""
        before_item_index = _find_date_position(date, [item.date for item in self.items]) - 1
        before_item = self.items[before_item_index]
        new_item = WealthItem(
            date=date, asset=before_item.asset + Decimal(volume), currency=before_item.currency - Decimal(investment)
        )

        # if any following items, update them too
        for _item in self.items[before_item_index + 1 :]:
            _item.add_currency(-investment)  # investing equals removing currency
            _item.add_asset(volume)
        self.items.insert(before_item_index + 1, new_item)

    def invest(self, date: datetime, investment: float, volume: float) -> None:
        """Put money in the market, receive a certain volume of an asset."""
        self._new_entry(date)
        self._update_wealth(date, investment, volume)

    def withdraw(self, date: datetime, withdraw: float, volume: float) -> None:
        """Remove asset from the market, receive a certain amount of currency."""
        self._new_exit(date)
        self._update_wealth(date, -withdraw, -volume)


def _find_date_position(date: datetime, date_collection: list[datetime]) -> int:
    """Find the index to insert the input date in the ordered collection."""
    for index, date_i in enumerate(reversed(date_collection)):
        if date >= date_i:
            return len(date_collection) - index
    return 0


class Portfolio:
    """Represent a trading portfolio.

    The portfolio expects to be updated with trades ordered by date.
    It cannot process trades that are older than the last processed trade.

    Args:
        starting_date: date when the series begins
        starting_asset: available assets at the start of the series
        starting_currency: available currency at the start of the series
    """

    wealth_series: WealthSeries

    def __init__(self, starting_date: datetime, starting_asset: float, starting_currency: float):
        wealth_items = [
            WealthItem(
                date=starting_date,
                asset=Decimal(starting_asset),
                currency=Decimal(starting_currency),
            )
        ]
        self.wealth_series = WealthSeries(items=wealth_items, actions=[])

    def _perform_entry(self, date: datetime, investment: float, volume: float) -> None:
        """Enter the market if the portfolio wealth allows it."""
        if self.wealth_series.entries_after(date):
            raise ValueError("Cannot enter the market before an existing entry.")

        if self.wealth_series.get_currency_at(date) < investment:
            raise ValueError("Not enough capital to enter the market.")

        self.wealth_series.invest(date, investment, volume)

    def _perform_exit(self, date: datetime, volume: float, withdraw: float) -> None:
        """Exit from a position."""
        if self.wealth_series.get_asset_at(date) < volume:
            raise ValueError("Cannot exit the market, asset volume too small.")

        self.wealth_series.withdraw(date, withdraw, volume)

    def get_available_capital_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        return self.wealth_series.get_currency_at(date)

    def get_asset_volume_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        return self.wealth_series.get_asset_at(date)
