from datetime import datetime
from decimal import Decimal

import pytest

from ptahlmud.backtesting.portfolio import Portfolio, TimedAction, WealthItem, WealthSeries
from ptahlmud.types.signal import Action


def test_wealth_series_update_wealth_after_date():
    """Check items after the new item date are updated."""
    wealth_series = WealthSeries(
        items=[
            WealthItem(date=datetime(2020, 1, 1), asset=Decimal(2), currency=Decimal(80)),
            WealthItem(date=datetime(2020, 1, 3), asset=Decimal(1), currency=Decimal(90)),
        ],
        actions=[TimedAction(date=datetime(2020, 1, 3), action=Action.EXIT)],
    )
    wealth_series.invest(date=datetime(2020, 1, 2), investment=-10, volume=-1)

    last_item = wealth_series.items[-1]

    assert last_item.date == datetime(2020, 1, 3)
    assert last_item.asset == Decimal(0)
    assert last_item.currency == Decimal(100)


def test_portfolio():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    assert len(portfolio.wealth_series.items) == 1

    wealth_item = portfolio.wealth_series.items[0]
    assert wealth_item.date == datetime(2020, 1, 1)
    assert wealth_item.asset == 0
    assert wealth_item.currency == 100


def test__perform_entry():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    portfolio._perform_entry(datetime(2020, 1, 2), 10, 1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 1

    portfolio._perform_entry(datetime(2020, 1, 3), 20, 1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 70
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 2

    portfolio._perform_entry(datetime(2020, 1, 4), -30, 1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 4)) == 100
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 4)) == 3


def test__perform_entry_fails_before_start_date():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    with pytest.raises(ValueError, match="Cannot enter the market before the initial date."):
        portfolio._perform_entry(datetime(2019, 12, 31), 10, 1)


def test__perform_entry_fails_existing_entry_before():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    portfolio._perform_entry(datetime(2020, 1, 2), 10, 1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90

    with pytest.raises(ValueError, match="Cannot enter the market before an existing entry."):
        portfolio._perform_entry(datetime(2020, 1, 1), 10, 1)


def test__perform_entry_fails_low_capital():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    with pytest.raises(ValueError, match="Not enough capital to enter the market."):
        portfolio._perform_entry(datetime(2020, 1, 1), 110, 1)


def test__perform_exit():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=1, starting_currency=0)

    assert portfolio.get_available_capital_at(datetime(2020, 1, 1)) == 0
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 1)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), volume=1, withdraw=10)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 0


def test__perform_exit_updates_following_exit():
    """Check that the following exit is updated."""
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=2, starting_currency=0)

    portfolio._perform_exit(datetime(2020, 1, 3), volume=1, withdraw=10)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), volume=1, withdraw=10)

    # check the previous exit state
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 20
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 0


def test__perform_exit_fails_on_volume():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=1, starting_currency=0)

    with pytest.raises(ValueError, match="Cannot exit the market, asset volume too small."):
        portfolio._perform_exit(datetime(2020, 1, 2), volume=2, withdraw=20)
