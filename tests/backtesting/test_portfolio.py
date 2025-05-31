from datetime import datetime

from ptahlmud.backtesting.portfolio import Portfolio


def test_portfolio():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)
    assert portfolio is not None
