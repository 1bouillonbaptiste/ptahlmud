"""Backtesting processing module.

This module is responsible for processing trading orders given by strategies.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from ptahlmud.backtesting.portfolio import Portfolio
from ptahlmud.backtesting.trades import TradingTarget, calculate_trade
from ptahlmud.backtesting.trading import Trade
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.signal import Action, Side, Signal


class RiskConfig(BaseModel):
    """Define risk configuration.

    Attributes:
        size: fraction of available capital to use for trading
        take_profit: close the position when the profit reaches this value
        stop_loss: close the position when the loss reaches this value
    """

    size: float
    take_profit: float
    stop_loss: float


@dataclass
class MatchedSignal:
    """Represent two associated signals.

    An entry can be associated with an exit if it is known, the exit is the latest date until a position is hold.
    Sometimes, a trader enters the market without knowing when to exit.
    """

    entry: Signal
    exit: Signal | None

    @property
    def exit_date(self) -> datetime | None:
        """Return the date of the exit signal."""
        if self.exit is None:
            return None
        return self.exit.date


def _match_signals(signals: list[Signal]) -> list[MatchedSignal]:
    """Group entries to exits.

    An exit closes every previous entry, exits count doesn't need to match entries count.
    """

    def _find_next_exit(remaining_signals: list[Signal], side: Side) -> Signal | None:
        """Find the first exit of the specified side."""
        for _signal in remaining_signals:
            if _signal.action != Action.EXIT:
                continue
            if _signal.side == side:
                return _signal
        return None

    signals = sorted(signals, key=lambda s: s.date)
    matches: list[MatchedSignal] = []
    for index, signal in enumerate(signals):
        if signal.action == Action.ENTER:
            exit_signal = _find_next_exit(signals[index:], side=signal.side)
            matches.append(MatchedSignal(entry=signal, exit=exit_signal))
    return matches


def _create_target(match: MatchedSignal, risk_config: RiskConfig) -> TradingTarget:
    """Create an instance of `TradingTarget`."""
    if match.entry.side == Side.LONG:
        return TradingTarget(
            high=risk_config.take_profit,
            low=risk_config.stop_loss,
        )
    else:
        return TradingTarget(
            high=risk_config.stop_loss,
            low=min(risk_config.take_profit, 0.999),  # the maximum profit is 100% if the price goes at 0
        )


def process_signals(
    signals: list[Signal],
    risk_config: RiskConfig,
    fluctuations: Fluctuations,
    initial_portfolio: Portfolio,
) -> tuple[list[Trade], Portfolio]:
    """Simulate the market from user-defined trading signals."""
    portfolio = deepcopy(initial_portfolio)
    fluctuations_end_time = fluctuations.candles[-1].open_time
    trades: list[Trade] = []
    for match in _match_signals(signals):
        available_capital = portfolio.get_available_capital_at(match.entry.date)
        if available_capital == 0:
            continue

        if match.entry.date >= fluctuations_end_time:
            continue

        fluctuations_subset = fluctuations.subset(from_date=match.entry.date, to_date=match.exit_date)
        new_trade = calculate_trade(
            open_at=match.entry.date,
            money_to_invest=available_capital * risk_config.size,
            fluctuations=fluctuations_subset,
            target=_create_target(match=match, risk_config=risk_config),
            side=match.entry.side,
        )
        trades.append(new_trade)
        portfolio.update_from_trade(new_trade)
    return trades, portfolio
