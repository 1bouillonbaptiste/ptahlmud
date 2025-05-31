"""Backtesting processing module.

This module is responsible to process trading orders given by strategies.

# TODO: create Portfolio to manage an asset and capital during the backtest
#       it must implement .get(size: CapitalSize) and .update(trade:Trade)
# TODO: create CapitalSize which is a volume or a percentage of available capital for trading
# TODO: match entry and exit Signal into a MatchedSignal
# TODO :calculate a trade from a matched signal
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from ptahlmud.backtesting.exposition import Trade
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.signal import Action, Side, Signal


class RiskConfig(BaseModel):
    """Define risk configuration.

    # TODO: find a name for higher and lower barriers

    Attributes:
        size: capital to gamble at each trade
    """

    size: Any


@dataclass
class MatchedSignal:
    """Represent two associated signals.

    An entry can be associated with an exit if it is known, the exit is the latest date until a position is hold.
    Sometimes, a trader enters the market without knowing when to exit.
    """

    entry: Signal
    exit: Signal | None


def _match_signals(signals: list[Signal]) -> list[MatchedSignal]:
    """Group entries to exits.

    An exit closes every previous entry, exits count doesn't need to match entries count.
    """

    def _find_next_exit(remaining_signals: list[Signal], side: Side) -> Signal | None:
        """Find the first exit of the specified side."""
        for signal in remaining_signals:
            if signal.action != Action.EXIT:
                continue
            if signal.side == side:
                return signal
        return None

    signals = sorted(signals, key=lambda signal: signal.date)
    matches: list[MatchedSignal] = []
    for index, signal in enumerate(signals):
        if signal.action == Action.ENTER:
            exit_signal = _find_next_exit(signals[index:], side=signal.side)
            matches.append(MatchedSignal(entry=signal, exit=exit_signal))
    return matches


def _process_signals(signals: list[Signal], risk_config: RiskConfig, fluctuations: Fluctuations) -> list[Trade]:
    """Simulate the market from user-defined trading signals."""
    return []
