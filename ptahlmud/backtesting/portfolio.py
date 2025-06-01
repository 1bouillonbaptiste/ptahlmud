"""Define `Portfolio`.

When trading, the money comes from a portfolio and is exchanged for a certain volume of an asset.
Each trade uses a certain amount of free capital, which grows and shrinks over time.
To know exactly the state of a portfolio over time, we register the wealth over time and update it according to trades.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ptahlmud.backtesting.exposition import Trade


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


@dataclass
class WealthSeries:
    """Store the wealth of a portfolio over time.

    Items and signals are always ordered by date.

    Attributes:
        items: wealth time series values
        entries: dates when the portfolio entered the market as a list
    """

    items: list[WealthItem]
    entries: list[datetime]

    def entries_after(self, date: datetime) -> bool:
        """Check if there are any entries after a given date."""
        if not self.entries:
            return False
        return date < self.entries[-1]

    def get_currency_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return float(self.items[item_index].currency)

    def get_asset_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        item_index = _find_date_position(date=date, date_collection=[item.date for item in self.items]) - 1
        return float(self.items[item_index].asset)

    def new_entry(self, date: datetime) -> None:
        """Create a new timed entry in the series."""
        if date < self.items[0].date:
            raise ValueError("Cannot enter the market before the initial date.")
        self.entries.insert(_find_date_position(date, self.entries), date)

    def update_wealth(self, date: datetime, currency_difference: float, asset_difference: float) -> None:
        """Increase the wealth from `date` by `currency_difference` and `asset_difference`."""
        before_item_index = _find_date_position(date, [item.date for item in self.items]) - 1
        before_item = self.items[before_item_index]
        new_item = WealthItem(
            date=date,
            asset=before_item.asset + Decimal(str(asset_difference)),
            currency=before_item.currency + Decimal(str(currency_difference)),
        )

        # if any following items, update them too
        for _item in self.items[before_item_index + 1 :]:
            _item.add_currency(currency_difference)
            _item.add_asset(asset_difference)
        self.items.insert(before_item_index + 1, new_item)


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
        self.wealth_series = WealthSeries(items=wealth_items, entries=[])

    def _perform_entry(self, date: datetime, currency_amount: float, asset_volume: float) -> None:
        """Enter the market by investing `currency_amount` to gain `asset_volume`."""
        if self.wealth_series.entries_after(date):
            raise ValueError("Cannot enter the market before an existing entry.")

        if self.wealth_series.get_currency_at(date) < currency_amount:
            raise ValueError("Not enough capital to enter the market.")

        self.wealth_series.new_entry(date=date)
        self.wealth_series.update_wealth(date=date, currency_difference=-currency_amount, asset_difference=asset_volume)

    def _perform_exit(self, date: datetime, currency_amount: float, asset_volume: float) -> None:
        """Exit the market by selling `volume` of an asset for `withdraw`."""
        if self.wealth_series.get_asset_at(date) < asset_volume:
            raise ValueError("Cannot exit the market, asset volume too small.")

        self.wealth_series.update_wealth(date=date, currency_difference=currency_amount, asset_difference=-asset_volume)

    def update_from_trade(self, trade: Trade) -> None:
        """Update the portfolio state with a new trade."""
        self._perform_entry(trade.open_date, currency_amount=trade.initial_investment, asset_volume=trade.volume)
        self._perform_exit(
            trade.close_date, asset_volume=trade.volume, currency_amount=trade.total_profit + trade.initial_investment
        )

    def get_available_capital_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        return self.wealth_series.get_currency_at(date)

    def get_asset_volume_at(self, date: datetime) -> float:
        """Return the money free to be invested."""
        return self.wealth_series.get_asset_at(date)
