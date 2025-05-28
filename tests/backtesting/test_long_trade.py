import random
from dataclasses import replace
from datetime import datetime

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as some
from hypothesis.strategies import composite
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.exposition import Position, open_position
from ptahlmud.backtesting.long_trade import (
    ExitSignal,
    _get_lower_bound_index,
    _get_position_exit_signal,
    calculate_long_trade,
)
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.testing.generate import generate_candles
from ptahlmud.types.candle import Candle
from ptahlmud.types.period import Period


class GetLowerBoundIndexCases:
    """Generate cases for `_get_lower_bound_index`.

    Each case returns:
    - a date
    - candle to find the lower-bound index in
    - the expected_index
    """

    def case_date_before_candles(self):
        return datetime(2023, 1, 1), generate_candles(size=10, from_date=datetime(2023, 1, 2)), 0

    def case_date_after_candles(self):
        return datetime(2024, 1, 1), generate_candles(size=10, from_date=datetime(2023, 1, 2)), 10

    def case_date_is_first_candle_close(self):
        return (
            datetime(2023, 1, 1, 1),
            generate_candles(size=10, period=Period(timeframe="1h"), from_date=datetime(2023, 1, 1)),
            1,
        )

    def case_date_is_last_candle_open(self):
        return (
            datetime(2023, 1, 1, 9),
            generate_candles(size=10, period=Period(timeframe="1h"), from_date=datetime(2023, 1, 1)),
            9,
        )

    def case_date_in_the_middle(self):
        """3 nested iterations, 5 + 2 + 0."""
        return (
            datetime(2023, 1, 1, 7),
            generate_candles(size=10, period=Period(timeframe="1h"), from_date=datetime(2023, 1, 1)),
            7,
        )


@parametrize_with_cases("date, candles, expected_index", cases=GetLowerBoundIndexCases)
def test__get_lower_bound_index(date, candles, expected_index):
    index = _get_lower_bound_index(date, candles)
    assert index == expected_index


@pytest.fixture
def fake_position() -> Position:
    return open_position(open_date=datetime(2024, 8, 20), open_price=100, money_to_invest=50, fees_pct=0.001)


@pytest.fixture
def candle():
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

    def case_take_profit_at_high_time(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, take_profit=110),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="take_profit", date_signal="high"),
        )

    def case_stop_loss_at_low_time(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, stop_loss=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="stop_loss", date_signal="low"),
        )

    def case_exit_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close pice."""
        return (
            replace(fake_position, take_profit=105, stop_loss=95),
            candle,
            ExitSignal(price_signal="close", date_signal="close"),
        )

    def case_take_profit_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close price."""
        return (
            replace(fake_position, take_profit=105),
            candle,
            ExitSignal(price_signal="take_profit", date_signal="close"),
        )

    def case_stop_loss_undefined_time(self, fake_position, candle):
        """High and low times are None, take close time and close price."""
        return (
            replace(fake_position, stop_loss=95),
            candle,
            ExitSignal(price_signal="stop_loss", date_signal="close"),
        )

    def case_tp_before_sl(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=13)
        return (
            replace(fake_position, take_profit=105, stop_loss=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="take_profit", date_signal="high"),
        )

    def case_sl_before_tp(self, fake_position, candle):
        high_time = datetime(2024, 8, 25, hour=12)
        low_time = datetime(2024, 8, 25, hour=3)
        return (
            replace(fake_position, take_profit=105, stop_loss=95),
            replace(candle, high_time=high_time, low_time=low_time),
            ExitSignal(price_signal="stop_loss", date_signal="low"),
        )


@parametrize_with_cases("position, current_candle, expected_signal", cases=GetPositionExitSignalCases)
def test__get_position_exit_signal(position, current_candle, expected_signal):
    signal = _get_position_exit_signal(position, current_candle)
    assert signal == expected_signal


@composite
def some_fluctuations(draw) -> Fluctuations:
    total_candles = some.integers(min_value=10, max_value=100)

    period = Period(timeframe="1m")
    candles: list[Candle] = generate_candles(size=draw(total_candles), period=period)
    return Fluctuations(candles=candles, period=period)


@given(some_fluctuations())
def test_calculate_long_trade(fluctuations: Fluctuations):
    # The better here would be to draw a random candle using hypothesis.
    candle: Candle = random.choice(fluctuations.candles)  # noqa: S311
    trade = calculate_long_trade(candle=candle, fluctuations=fluctuations, take_profit_pct=0.05, stop_loss_pct=0.05)
    if trade is not None:
        assert np.sign(trade.close_price - trade.open_price) == np.sign(trade.total_profit + trade.total_fees)
        assert trade.open_date < trade.close_date
