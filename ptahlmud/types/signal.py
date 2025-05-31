"""Define a trading signal."""

import datetime
import enum
from dataclasses import dataclass


class Side(str, enum.Enum):
    """Define the trading side.

    A **long** trade follows the market, the trader expects an asset price to go up.
    A **short** trade is against the market, the trader expects an asset price to go down.
    """

    LONG = "LONG"
    SHORT = "SHORT"


class Action(str, enum.Enum):
    """Define the trade action.

    **Enter** means the trader enters the market with a specific side.
    **Exit** means the trader leaves the market from its position.
    **Hold** means the trader waits; he holds its position.
    """

    ENTER = "ENTER"
    EXIT = "EXIT"
    HOLD = "HOLD"


@dataclass(slots=True)
class Signal:
    """Represent a trading signal.

    Attributes:
        date: date of the signal
        side: side of the signal
        action: what action to take
    """

    date: datetime.datetime
    side: Side
    action: Action
