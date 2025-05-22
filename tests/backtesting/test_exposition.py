import datetime

import pytest

from ptahlmud.backtesting.exposition import Position, close_position, open_position


@pytest.fixture
def fake_position() -> Position:
    return open_position(open_date=datetime.datetime(2024, 8, 20), open_price=100, money_to_invest=50, fees_pct=0.001)


def test_open_position(fake_position):
    assert fake_position.initial_investment == 50
    assert fake_position.open_fees == 0.05
    assert fake_position.volume == pytest.approx(0.4995, abs=1e-5)
    assert fake_position.volume * fake_position.open_price + fake_position.open_fees == 50


def test_close_position(fake_position):
    trade = close_position(position=fake_position, close_date=datetime.datetime(2024, 8, 25), close_price=125)

    assert trade.close_fees == 125 * fake_position.volume * 0.001
    assert trade.total_fees == 125 * fake_position.volume * 0.001 + fake_position.open_fees
    assert trade.total_profit == pytest.approx(fake_position.volume * 125 - 50 - trade.close_fees)
    assert trade.total_duration == datetime.timedelta(days=5)
