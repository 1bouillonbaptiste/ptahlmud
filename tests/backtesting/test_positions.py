from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as some
from hypothesis.strategies import composite

from ptahlmud.backtesting.position import Position
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


def test_open_position(fake_position):
    assert fake_position.initial_investment == 50
    assert fake_position.open_fees == 0.05
    assert fake_position.volume == pytest.approx(0.4995, abs=1e-5)
    assert fake_position.volume * fake_position.open_price + fake_position.open_fees == 50


def test_close_position(fake_position):
    trade = fake_position.close(close_date=datetime(2024, 8, 25), close_price=125)

    expected_close_fees = 125 * fake_position.volume * 0.001
    assert trade.close_fees == pytest.approx(expected_close_fees)
    assert trade.total_fees == pytest.approx(expected_close_fees + fake_position.open_fees)
    assert trade.total_profit == pytest.approx(fake_position.volume * 125 - 50 - trade.close_fees)
    assert trade.total_duration == timedelta(days=5)


@composite
def valid_position_parameters(draw) -> dict[str, Any]:
    open_date = draw(some.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2050, 12, 31)))

    open_price = draw(some.decimals(min_value=Decimal("0.01"), max_value=Decimal("1_000_000")))

    money_to_invest = draw(some.decimals(min_value=Decimal("0.01"), max_value=Decimal("1_000_000")))

    fees_pct = draw(some.decimals(min_value=Decimal("0.0001"), max_value=Decimal("0.1")))

    side = draw(some.sampled_from([Side.LONG, Side.SHORT]))

    # Ensure higher barrier > open_price
    higher_barrier = draw(
        some.decimals(min_value=open_price * Decimal("1.001"), max_value=open_price * Decimal("1000"))
    )

    # Ensure lower barrier < open_price
    lower_barrier = draw(some.decimals(min_value=open_price * Decimal("0.0"), max_value=open_price * Decimal("0.999")))

    return {
        "open_date": open_date,
        "open_price": float(open_price),
        "money_to_invest": float(money_to_invest),
        "fees_pct": float(fees_pct),
        "side": side,
        "higher_barrier": float(higher_barrier),
        "lower_barrier": float(lower_barrier),
    }


@composite
def valid_trade_parameters(draw) -> tuple[dict[str, Any], dict[str, Any]]:
    position_params = draw(valid_position_parameters())

    # Generate close_date after open_date
    close_date = draw(
        some.datetimes(
            min_value=position_params["open_date"], max_value=position_params["open_date"] + timedelta(days=365)
        )
    )

    # Generate close_price between lower and higher barriers
    close_price = draw(
        some.decimals(
            min_value=Decimal(str(position_params["lower_barrier"])),
            max_value=Decimal(str(position_params["higher_barrier"])),
        )
    )

    return position_params, {
        "close_date": close_date,
        "close_price": float(close_price),
    }


@given(valid_position_parameters())
def test_position_properties(params):
    position = Position.open(**params)

    assert position.initial_investment > 0
    assert position.volume > 0
    assert position.open_price > 0
    assert position.fees_pct > 0

    # logical constraints
    assert position.lower_barrier < position.open_price
    assert position.higher_barrier > position.open_price
    assert not position.is_closed

    # financial calculations
    assert position.open_fees == pytest.approx(position.initial_investment * position.fees_pct)
    assert position.volume * position.open_price + position.open_fees == pytest.approx(position.initial_investment)


@given(valid_trade_parameters())
def test_trade_properties(params):
    position_params, trade_params = params
    position = Position.open(**position_params)
    trade = position.close(**trade_params)

    # basic validation
    assert trade.is_closed
    assert trade.close_date >= trade.open_date
    assert trade.lower_barrier <= trade.close_price <= trade.higher_barrier
    assert trade.total_duration == (trade.close_date - trade.open_date)

    # financial calculations
    if trade.side == Side.LONG:
        expected_receipt = trade.volume * trade.close_price
    else:
        expected_receipt = trade.volume * (2 * trade.open_price - trade.close_price)
    max_error = 1e-3 if expected_receipt > 10_000 else 1e-7  # on large amounts, floating point errors can stack
    assert trade.receipt == pytest.approx(expected_receipt, abs=max_error)
    assert trade.open_fees == pytest.approx(trade.initial_investment * trade.fees_pct)
    assert trade.close_fees == pytest.approx(trade.receipt * trade.fees_pct)
    assert trade.total_fees == pytest.approx(trade.open_fees + trade.close_fees)

    # financial consistency
    trade_return = (trade.close_price - trade.open_price) * trade.volume
    if trade.side == Side.SHORT:
        trade_return *= -1
    expected_profit = trade_return - trade.total_fees
    assert trade.total_profit == pytest.approx(expected_profit)
