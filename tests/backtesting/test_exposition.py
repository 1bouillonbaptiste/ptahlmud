from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as some
from hypothesis.strategies import composite

from ptahlmud.backtesting.exposition import Position, Side, close_position, open_position


@pytest.fixture
def fake_position() -> Position:
    return open_position(open_date=datetime(2024, 8, 20), open_price=100, money_to_invest=50, fees_pct=0.001)


def test_open_position(fake_position):
    assert fake_position.initial_investment == 50
    assert fake_position.open_fees == 0.05
    assert fake_position.volume == pytest.approx(0.4995, abs=1e-5)
    assert fake_position.volume * fake_position.open_price + fake_position.open_fees == 50


def test_close_position(fake_position):
    trade = close_position(position=fake_position, close_date=datetime(2024, 8, 25), close_price=125)

    assert trade.close_fees == 125 * fake_position.volume * 0.001
    assert trade.total_fees == 125 * fake_position.volume * 0.001 + fake_position.open_fees
    assert trade.total_profit == pytest.approx(fake_position.volume * 125 - 50 - trade.close_fees)
    assert trade.total_duration == timedelta(days=5)


@composite
def valid_position_parameters(draw):
    open_date = draw(some.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2050, 12, 31)))

    open_price = draw(some.decimals(min_value=Decimal("0.01"), max_value=Decimal("1_000_000")))

    money_to_invest = draw(some.decimals(min_value=Decimal("0.01"), max_value=Decimal("1_000_000")))

    fees_pct = draw(some.decimals(min_value=Decimal("0.0001"), max_value=Decimal("0.1")))

    # Ensure take_profit > open_price
    take_profit = draw(some.decimals(min_value=open_price * Decimal("1.001"), max_value=open_price * Decimal("1000")))

    # Ensure stop_loss < open_price
    stop_loss = draw(some.decimals(min_value=open_price * Decimal("0.0"), max_value=open_price * Decimal("0.999")))

    return {
        "open_date": open_date,
        "open_price": float(open_price),
        "money_to_invest": float(money_to_invest),
        "fees_pct": float(fees_pct),
        "take_profit": float(take_profit),
        "stop_loss": float(stop_loss),
    }


@composite
def valid_trade_parameters(draw):
    position_params = draw(valid_position_parameters())
    position = open_position(**position_params)

    # Generate close_date after open_date
    close_date = draw(
        some.datetimes(
            min_value=position_params["open_date"], max_value=position_params["open_date"] + timedelta(days=365)
        )
    )

    # Generate close_price between stop_loss and take_profit
    close_price = draw(
        some.decimals(min_value=Decimal(str(position.stop_loss)), max_value=Decimal(str(position.take_profit)))
    )

    return position, close_date, float(close_price)


@given(valid_position_parameters())
def test_position_properties(params):
    position = open_position(**params)

    assert position.initial_investment > 0
    assert position.volume > 0
    assert position.open_price > 0
    assert position.fees_pct > 0

    # logical constraints
    assert position.stop_loss < position.open_price
    assert position.take_profit > position.open_price
    assert position.side == Side.LONG
    assert not position.is_closed

    # financial calculations
    assert position.open_fees == pytest.approx(position.initial_investment * position.fees_pct)
    assert position.volume * position.open_price + position.open_fees == pytest.approx(position.initial_investment)


@given(valid_trade_parameters())
def test_trade_properties(params):
    position, close_date, close_price = params
    trade = close_position(position, close_date, close_price)

    # basic validation
    assert trade.is_closed
    assert trade.close_date >= trade.open_date
    assert trade.stop_loss <= trade.close_price <= trade.take_profit
    assert trade.total_duration == (trade.close_date - trade.open_date)

    # financial calculations
    assert trade.receipt == pytest.approx(trade.volume * trade.close_price)
    assert trade.close_fees == pytest.approx(trade.receipt * trade.fees_pct)
    assert trade.total_fees == pytest.approx(trade.open_fees + trade.close_fees)

    # financial consistency
    expected_profit = (trade.close_price - trade.open_price) * trade.volume - trade.total_fees
    assert trade.total_profit == pytest.approx(expected_profit)
