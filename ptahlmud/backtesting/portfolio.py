"""Define `Portfolio`.

When trading, the money comes from a portfolio and is exchanged for a certain volume of an asset.
Each trade uses a certain amount of free capital, which grows and shrinks over time.
To know exactly the state of a portfolio over time, we register the wealth over time and update it according to trades.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class WealthItem:
    """Represent the state of a portfolio at a given time.

    Because we manage money and volumes, we use decimals to avoid rounding errors.
    """

    date: datetime
    asset: Decimal
    currency: Decimal


class Portfolio:
    """Represent a trading portfolio.

    A portfolio is the volume of an asset and amount of currency detained.

    Note: the portfolio manages a single asset. To deal with multiple coins, you can wrap the items
    in a new `WealthSeries` (or whatever name) class that is assigned to an asset.
    The current class would be responsible for updating the series corresponding to a traded asset.

    Args:
        starting_date: date when the series begins
        starting_asset: available assets at the start of the series
        starting_currency: available currency at the start of the series
    """

    _items: list[WealthItem]

    def __init__(self, starting_date: datetime, starting_asset: float, starting_currency: float):
        self._items = [
            WealthItem(
                date=starting_date,
                asset=Decimal(starting_asset),
                currency=Decimal(starting_currency),
            )
        ]
