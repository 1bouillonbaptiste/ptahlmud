from dataclasses import replace
from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as some
from hypothesis.strategies import composite
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.trades import (
    BarrierLevels,
    ExitSignal,
    _get_position_exit_signal,
    calculate_trade,
)
from ptahlmud.backtesting.trading import Position, Trade
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.testing.generate import generate_candles
from ptahlmud.types.candle import Candle
from ptahlmud.types.period import Period
from ptahlmud.types.signal import Side


@pytest.fixture
def fake_position() -> Position:
    return Position.open(
        open_date=datetime(2024, 8, 20),
        open_price=100,
        money_to_invest=50,
        fees_pct=0.001,
        side=Side.LONG,
    )


@pytest.fixture
def candle() -> Candle:
    return Candle(
        open_time=datetime(2024, 8, 25),
        close_time=datetime(2024, 8, 26),
        high_time=None,
        low_time=None,
        open=100,
        high=110,
        low=90,
        close=100,
        volume=50,
        total_trades=1,
    )


class GetPositionExitSignalCases:
    """Generate cases for `_get_position_exit_signal()`.

    Each case returns:
    - a position to analyse
    - a candle
    - the expected signal
    """

    def case_hold(self, fake_position, candle):
        """Position has no security, don't close it."""
        return fake_position, candle, ExitSignal(price_signal="hold", date_signal="hold")

    def case_higher_barrier_at_high_time(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, higher_barrier=110),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="high_barrier", date_signal="high"),
        )

    def case_lower_barrier_at_low_time(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, lower_barrier=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="low_barrier", date_signal="low"),
        )

    def case_exit_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close pice."""
        return (
            replace(fake_position, higher_barrier=105, lower_barrier=95),
            candle,
            ExitSignal(price_signal="close", date_signal="close"),
        )

    def case_higher_barrier_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close price."""
        return (
            replace(fake_position, higher_barrier=105),
            candle,
            ExitSignal(price_signal="high_barrier", date_signal="close"),
        )

    def case_lower_barrier_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close price."""
        return (
            replace(fake_position, lower_barrier=95),
            candle,
            ExitSignal(price_signal="low_barrier", date_signal="close"),
        )

    def case_tp_before_sl(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, higher_barrier=105, lower_barrier=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="high_barrier", date_signal="high"),
        )

    def case_sl_before_tp(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=3)
        return (
            replace(fake_position, higher_barrier=105, lower_barrier=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="low_barrier", date_signal="low"),
        )


@parametrize_with_cases("position, current_candle, expected_signal", cases=GetPositionExitSignalCases)
def test__get_position_exit_signal(position: Position, current_candle: Candle, expected_signal: ExitSignal):
    signal = _get_position_exit_signal(position, current_candle)
    assert signal == expected_signal


@composite
def some_fluctuations(draw) -> Fluctuations:
    total_candles = some.integers(min_value=10, max_value=100)

    period = Period(timeframe="1m")
    candles: list[Candle] = generate_candles(size=draw(total_candles), period=period)
    return Fluctuations(candles=candles, period=period)


@composite
def some_target(draw):
    higher_target = draw(some.floats(min_value=0.001, max_value=100))
    lower_target = draw(some.floats(min_value=0.001, max_value=0.999))
    return BarrierLevels(high=higher_target, low=lower_target)


@given(
    some_fluctuations(),
    some_target(),
    some.sampled_from([Side.LONG, Side.SHORT]),
)
def test_calculate_trade_target_properties(fluctuations: Fluctuations, target: BarrierLevels, side: Side):
    entry_candle: Candle = fluctuations.candles[0]
    trade = calculate_trade(
        open_at=entry_candle.close_time,
        money_to_invest=100,
        fluctuations=fluctuations,
        target=target,
        side=side,
    )

    higher_barrier = target.high_value(entry_candle.close)
    lower_barrier = target.low_value(entry_candle.close)

    assert trade.higher_barrier == pytest.approx(higher_barrier)
    assert trade.lower_barrier == pytest.approx(lower_barrier)

    # if trade reached target, the last candle contains high > higher target and / or low < lower target
    candles_during_trade = fluctuations.subset(from_date=trade.open_date, to_date=trade.close_date).candles[:-1]

    assert all(candle.high < higher_barrier for candle in candles_during_trade)
    assert all(candle.low > lower_barrier for candle in candles_during_trade)


@given(
    some_fluctuations(),
    some_target(),
    some.sampled_from([Side.LONG, Side.SHORT]),
)
def test_calculate_trade_temporal_properties(fluctuations: Fluctuations, target: BarrierLevels, side: Side):
    entry_candle: Candle = fluctuations.candles[0]
    trade = calculate_trade(
        open_at=entry_candle.close_time,
        money_to_invest=100,
        fluctuations=fluctuations,
        target=target,
        side=side,
    )
    assert trade.open_date == entry_candle.close_time
    assert trade.close_date > trade.open_date
    assert trade.close_date <= fluctuations.candles[-1].close_time


@given(
    some_fluctuations(),
    some_target(),
    some.sampled_from([Side.LONG, Side.SHORT]),
)
def test_calculate_trade_return_properties(fluctuations: Fluctuations, target: BarrierLevels, side: Side):
    entry_candle: Candle = fluctuations.candles[0]
    trade = calculate_trade(
        open_at=entry_candle.close_time,
        money_to_invest=100,
        fluctuations=fluctuations,
        target=target,
        side=side,
    )

    def _is_profitable_fees_free(some_trade: Trade) -> bool:
        """Check if a trade is profitable when fees are removed."""
        return some_trade.total_profit + some_trade.total_fees > 0

    def _is_long(some_trade: Trade) -> bool:
        """Check if a trade is a LONG trade."""
        return some_trade.side == Side.LONG

    if trade.close_price == trade.open_price:
        assert trade.total_profit + trade.total_fees == 0
    elif trade.close_price > trade.open_price:
        if _is_long(trade):
            assert _is_profitable_fees_free(trade)
        else:
            assert not _is_profitable_fees_free(trade)
    else:
        if _is_long(trade):
            assert not _is_profitable_fees_free(trade)
        else:
            assert _is_profitable_fees_free(trade)
