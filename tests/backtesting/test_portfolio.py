from datetime import datetime
from decimal import Decimal

import pytest
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.exposition import Trade, close_position, open_position
from ptahlmud.backtesting.portfolio import Portfolio, TimedAction, WealthItem, WealthSeries
from ptahlmud.types.signal import Action, Side


def test_wealth_series_update_wealth_after_date():
    """Check items after the new item date are updated."""
    wealth_series = WealthSeries(
        items=[
            WealthItem(date=datetime(2020, 1, 1), asset=Decimal(2), currency=Decimal(80)),
            WealthItem(date=datetime(2020, 1, 3), asset=Decimal(1), currency=Decimal(90)),
        ],
        actions=[TimedAction(date=datetime(2020, 1, 3), action=Action.EXIT)],
    )
    wealth_series.update_wealth(date=datetime(2020, 1, 2), currency_difference=10, asset_difference=-1)

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

    portfolio._perform_entry(datetime(2020, 1, 2), currency_amount=10, asset_volume=1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 1

    portfolio._perform_entry(datetime(2020, 1, 3), currency_amount=20, asset_volume=1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 70
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 2

    portfolio._perform_entry(datetime(2020, 1, 4), currency_amount=-30, asset_volume=1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 4)) == 100
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 4)) == 3


def test__perform_entry_fails_before_start_date():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    with pytest.raises(ValueError, match="Cannot enter the market before the initial date."):
        portfolio._perform_entry(datetime(2019, 12, 31), currency_amount=10, asset_volume=1)


def test__perform_entry_fails_existing_entry_before():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    portfolio._perform_entry(datetime(2020, 1, 2), currency_amount=10, asset_volume=1)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90

    with pytest.raises(ValueError, match="Cannot enter the market before an existing entry."):
        portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=10, asset_volume=1)


def test__perform_entry_fails_low_capital():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=100)

    with pytest.raises(ValueError, match="Not enough capital to enter the market."):
        portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=110, asset_volume=1)


def test__perform_exit():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=1, starting_currency=0)

    assert portfolio.get_available_capital_at(datetime(2020, 1, 1)) == 0
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 1)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=1, currency_amount=10)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 0


def test__perform_exit_updates_following_exit():
    """Check that the following exit is updated."""
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=2, starting_currency=0)

    portfolio._perform_exit(datetime(2020, 1, 3), asset_volume=1, currency_amount=10)
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=1, currency_amount=10)

    # check the previous exit state
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 20
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 0


def test__perform_exit_fails_on_volume():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=1, starting_currency=0)

    with pytest.raises(ValueError, match="Cannot exit the market, asset volume too small."):
        portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=2, currency_amount=20)


class PortfolioUpdateFromTradeCases:
    """Generate test cases for `Portfolio.update_from_trade()`.

    The portfolio is initialized with currency at 200 and volume at 0.

    Each trade returns:
    - a trade to update the default portfolio with
    - expected wealth at different dates
    """

    def case_long_trade(self):
        fees_pct = 0.1
        position = open_position(
            open_date=datetime(2020, 1, 1),
            open_price=10,
            money_to_invest=100,
            fees_pct=fees_pct,  # take 10% from 100, volume is 9
            side=Side.LONG,
        )
        trade = close_position(position, close_date=datetime(2020, 1, 3), close_price=20)
        selling_receipt = 9 * 20 * (1 - fees_pct)
        return trade, [
            WealthItem(date=datetime(2020, 1, 1), asset=Decimal(9), currency=Decimal(100)),
            WealthItem(date=datetime(2020, 1, 3), asset=Decimal(0), currency=Decimal(100 + selling_receipt)),
        ]

    def case_short_trade(self):
        money_to_invest = 100
        position = open_position(
            open_date=datetime(2020, 1, 1),
            open_price=100,
            money_to_invest=money_to_invest,
            fees_pct=0.1,  # take 10% from 100, volume is 0.9
            side=Side.SHORT,
        )
        trade = close_position(position, close_date=datetime(2020, 1, 3), close_price=110)
        selling_return = trade.total_profit + money_to_invest
        return trade, [
            WealthItem(date=datetime(2020, 1, 1), asset=Decimal("0.9"), currency=Decimal(100)),
            WealthItem(date=datetime(2020, 1, 3), asset=Decimal(0), currency=Decimal(100 + selling_return)),
        ]


@parametrize_with_cases("trade, expected_wealth_at_dates", cases=PortfolioUpdateFromTradeCases)
def test_portfolio_update_from_trade(trade: Trade, expected_wealth_at_dates: list[WealthItem]):
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1), starting_asset=0, starting_currency=200)
    portfolio.update_from_trade(trade)
    for wealth_item in expected_wealth_at_dates:
        assert portfolio.get_available_capital_at(wealth_item.date) == float(wealth_item.currency)
        assert portfolio.get_asset_volume_at(wealth_item.date) == float(wealth_item.asset)
