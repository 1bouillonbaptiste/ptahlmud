from datetime import datetime

from ptahlmud.backtesting.portfolio import Portfolio


def test_portfolio():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    assert len(portfolio.wealth_series.items) == 1

    wealth_item = portfolio.wealth_series.items[0]
    assert wealth_item.date == datetime(2020, 1, 1)
    assert wealth_item.asset == 0
    assert wealth_item.currency == 100
