import datetime

import pytest

from ptahlmud.backtesting.exposition import open_position


def test_open_position():
    position = open_position(open_date=datetime.datetime(2020, 1, 1), open_price=100, money_to_invest=50)
    assert position.initial_investment == 50
    assert position.open_fees == 0.05
    assert position.volume == pytest.approx(0.4995, abs=1e-5)
    assert position.volume * position.open_price + position.open_fees == 50
