"""Backtesting processing module.

This module is responsible to process trading orders given by strategies.

# TODO: create Portfolio to manage an asset and capital during the backtest
#       it must implement .get(size: CapitalSize) and .update(trade:Trade)
# TODO: create CapitalSize which is a volume or a percentage of available capital for trading
# TODO: match entry and exit Signal into a MatchedSignal
# TODO :calculate a trade from a matched signal
"""

from typing import Any

from pydantic import BaseModel

from ptahlmud.backtesting.exposition import Trade
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.signal import Signal


class RiskConfig(BaseModel):
    """Define risk configuration.

    # TODO: find a name for higher and lower barriers

    Attributes:
        size: capital to gamble at each trade
    """

    size: Any


def _process_signals(signals: list[Signal], risk_config: RiskConfig, fluctuations: Fluctuations) -> list[Trade]:
    """Simulate the market from user-defined trading signals."""
    return []
