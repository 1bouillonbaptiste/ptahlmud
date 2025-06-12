"""Process trading signals for backtesting.

This module converts trading signals into executed trades by simulating
market interactions according to risk management rules. It handles:

1. Signal matching (pairing entry and exit signals)
2. Risk management (position sizing, take-profit and stop-loss levels)
3. Trade simulation (calculating exact entry/exit points and results)
4. Portfolio tracking (recording changes in capital and asset holdings)

The core functionality is encapsulated in `process_signals()`, which transforms
a sequence of raw trading signals into a list of executed trades and an updated portfolio.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from ptahlmud.backtesting.operations import BarrierLevels, calculate_trade
from ptahlmud.backtesting.portfolio import Portfolio
from ptahlmud.backtesting.position import Trade
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.signal import Action, Side, Signal


class RiskConfig(BaseModel):
    """Define risk management parameters for trading.

    Risk management is crucial for protecting trading capital. This configuration
    determines how much capital to risk per trade and when to exit positions.

    Attributes:
        size: the fraction of available capital to allocate to each trade
        take_profit: the price increase percentage that triggers profit-taking
        stop_loss: the price decrease percentage that triggers loss-cutting
    """

    size: float
    take_profit: float
    stop_loss: float


@dataclass
class MatchedSignal:
    """Pair entry and exit signals for a complete trading operation.

    A matched signal represents the full lifecycle of a potential trade, from
    market entry to exit. The exit may be predetermined or determined during
    the trading process based on price action.

    Attributes:
        entry: the signal indicating when to enter the market and in which direction
        exit: the signal indicating when to exit, it can be None if there is no trading time limit
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
    """Group entry signals with their corresponding exit signals.

    This function pairs ENTER signals with the next EXIT signal of the matching side.
    One EXIT signal can close multiple ENTER signals of the same side.

    Args:
        signals: A list of trading signals (ENTER, EXIT, HOLD) to be matched

    Returns:
        A list of matched signals, each containing an entry and possibly an exit
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


def _create_target(match: MatchedSignal, risk_config: RiskConfig) -> BarrierLevels:
    """Create price barriers for a trade based on risk settings and trade direction."""

    if match.entry.side == Side.LONG:
        return BarrierLevels(
            high=risk_config.take_profit,
            low=risk_config.stop_loss,
        )
    else:
        return BarrierLevels(
            high=risk_config.stop_loss,
            low=min(risk_config.take_profit, 0.999),  # the maximum profit is 100% if the price goes at 0
        )


def process_signals(
    signals: list[Signal],
    risk_config: RiskConfig,
    fluctuations: Fluctuations,
) -> list[Trade]:
    """Process trading signals to generate trades and track portfolio changes.

    Args:
        signals: trading signals
        risk_config: risk management parameters
        fluctuations: market data

    Returns:
        executed trades as a list
        the portfolio after trading session
    """
    portfolio = Portfolio(starting_date=fluctuations.candles[0].open_time)
    fluctuations_end_time = fluctuations.candles[-1].open_time
    trades: list[Trade] = []
    trade_size = Decimal(str(risk_config.size))
    for match in _match_signals(signals):
        available_capital = portfolio.get_available_capital_at(match.entry.date)
        if available_capital == 0:
            continue

        if match.entry.date >= fluctuations_end_time:
            continue

        fluctuations_subset = fluctuations.subset(from_date=match.entry.date, to_date=match.exit_date)
        new_trade = calculate_trade(
            open_at=match.entry.date,
            money_to_invest=available_capital * trade_size,
            fluctuations=fluctuations_subset,
            target=_create_target(match=match, risk_config=risk_config),
            side=match.entry.side,
        )
        trades.append(new_trade)
        portfolio.update_from_trade(new_trade)
    return trades
