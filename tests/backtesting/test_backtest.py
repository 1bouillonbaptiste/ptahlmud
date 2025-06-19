from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as some
from hypothesis.strategies import composite
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.backtest import MatchedSignal, RiskConfig, _match_signals, process_signals
from ptahlmud.backtesting.portfolio import Portfolio
from ptahlmud.testing.generate import generate_candles
from ptahlmud.types.period import Period
from ptahlmud.types.signal import Action, Side, Signal


class MatchedSignalsCases:
    """Generate cases for `_match_signals()`.

    Each case returns:
    - signals to be matched
    - expected matches
    """

    def case_empty(self):
        return [], []

    def case_enter_long(self):
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        return [
            long_entry,
        ], [MatchedSignal(entry=long_entry, exit=None)]

    def case_exit_long(self):
        """No entry, so no action is performed."""
        long_exit = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.EXIT)
        return [
            long_exit,
        ], []

    def case_full_long(self):
        """Entry is associated to exit."""
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 2), side=Side.LONG, action=Action.EXIT)
        return [long_entry, long_exit], [MatchedSignal(entry=long_entry, exit=long_exit)]

    def case_long_exit_before_entry(self):
        long_entry = Signal(date=datetime(2020, 1, 3), side=Side.LONG, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 2), side=Side.LONG, action=Action.EXIT)
        return [long_entry, long_exit], [MatchedSignal(entry=long_entry, exit=None)]

    def case_different_side(self):
        """Don't match entry to exit if sides differ."""
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        short_exit = Signal(date=datetime(2020, 1, 2), side=Side.SHORT, action=Action.EXIT)
        return [long_entry, short_exit], [MatchedSignal(entry=long_entry, exit=None)]

    def case_mixed_side(self):
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        short_entry = Signal(date=datetime(2020, 1, 2), side=Side.SHORT, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 5), side=Side.LONG, action=Action.EXIT)
        short_exit = Signal(date=datetime(2020, 1, 4), side=Side.SHORT, action=Action.EXIT)
        return [long_entry, short_exit, short_entry, long_exit], [
            MatchedSignal(entry=long_entry, exit=long_exit),
            MatchedSignal(entry=short_entry, exit=short_exit),
        ]


@parametrize_with_cases("signals, expected_matches", cases=MatchedSignalsCases)
def test__match_signals(signals: list[Signal], expected_matches: list[MatchedSignal]):
    matches = _match_signals(signals)
    assert matches == expected_matches


@composite
def random_signal(draw) -> Signal:
    date = draw(some.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2020, 1, 1, minute=58)))
    side = draw(some.sampled_from(list(Side.__members__)))
    action = draw(some.sampled_from(list(Action.__members__)))
    return Signal(date=date, side=side, action=action)


@composite
def some_signals(draw) -> list[Signal]:
    """Generate a list of signals, one signal allowed per date."""
    max_signals = draw(some.integers(min_value=1, max_value=50))
    random_signals: list[Signal] = sorted([draw(random_signal()) for _ in range(max_signals)], key=lambda s: s.date)

    signals = [random_signals.pop()]
    for signal in signals:
        if signal.date > signals[-1].date:
            signals.append(signal)

    return signals


@composite
def some_risk_config(draw) -> RiskConfig:
    """Generate a random risk config."""
    return RiskConfig(
        size=draw(some.floats(min_value=0.01, max_value=1.0)),
        take_profit=draw(some.floats(min_value=0.001, max_value=100.0)),
        stop_loss=draw(some.floats(min_value=0.001, max_value=0.999)),
    )


@given(
    some_signals(),
    some_risk_config(),
)
def test_process_signals_trades_property(request, signals: list[Signal], risk_config: RiskConfig):
    """Check that trades are correctly generated from signals."""
    random_candles = generate_candles(
        from_date=datetime(2020, 1, 1), to_date=datetime(2020, 1, 1, hour=1), period=Period(timeframe="1m")
    )
    trades = process_signals(
        signals=signals,
        risk_config=risk_config,
        candles=random_candles,
    )

    # we don't trade when there is no capital, so we can have less trades than entry signals.
    assert len(trades) <= len([signal for signal in signals if signal.action == Action.ENTER])

    assert all(trade.volume > 0 for trade in trades)


@given(
    some_signals(),
    some_risk_config(),
)
def test_process_signals_portfolio_validity(request, signals: list[Signal], risk_config: RiskConfig):
    """Check that the portfolio state remains valid throughout the backtest."""
    random_candles = generate_candles(
        from_date=datetime(2020, 1, 1), to_date=datetime(2020, 1, 1, hour=1), period=Period(timeframe="1m")
    )
    trades = process_signals(signals=signals, risk_config=risk_config, candles=random_candles)

    if trades:
        portfolio = Portfolio(starting_date=trades[0].open_date)
        for trade in trades:
            portfolio.update_from_trade(trade)

        # every trade gets closed during the trading session, so the asset volume is the initial value
        assert portfolio.get_asset_volume_at(trades[-1].close_date) == Portfolio.default_asset_amount()
        total_profit = sum(trade.total_profit for trade in trades)
        assert portfolio.get_available_capital_at(trades[-1].close_date) == pytest.approx(
            portfolio.default_currency_amount() + total_profit
        )

        assert all(item.currency >= 0 for item in portfolio.wealth_series.items)
        assert all(item.asset >= 0 for item in portfolio.wealth_series.items)
