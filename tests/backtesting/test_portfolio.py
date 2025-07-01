from datetime import datetime
from decimal import Decimal

import pytest
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.models.signal import Side
from ptahlmud.backtesting.portfolio import Portfolio, WealthItem, WealthSeries
from ptahlmud.backtesting.positions import Position, Trade


def test_wealth_series_update_wealth_after_date():
    """Check items after the new item date are updated."""
    wealth_series = WealthSeries(
        items=[
            WealthItem(date=datetime(2020, 1, 1), asset=Decimal(2), currency=Decimal(80)),
            WealthItem(date=datetime(2020, 1, 3), asset=Decimal(1), currency=Decimal(90)),
        ],
        entries=[],
    )
    wealth_series.update_wealth(
        date=datetime(2020, 1, 2), currency_difference=Decimal(10), asset_difference=Decimal(-1)
    )

    last_item = wealth_series.items[-1]

    assert last_item.date == datetime(2020, 1, 3)
    assert last_item.asset == Decimal(0)
    assert last_item.currency == Decimal(100)


def test_portfolio():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    assert len(portfolio.wealth_series.items) == 1

    wealth_item = portfolio.wealth_series.items[0]
    assert wealth_item.date == datetime(2020, 1, 1)
    assert wealth_item.asset == 0
    assert wealth_item.currency == 100


def test__perform_entry():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    portfolio._perform_entry(datetime(2020, 1, 2), currency_amount=Decimal(10), asset_volume=Decimal(1))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 1

    portfolio._perform_entry(datetime(2020, 1, 3), currency_amount=Decimal(20), asset_volume=Decimal(1))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 70
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 2

    portfolio._perform_entry(datetime(2020, 1, 4), currency_amount=Decimal(-30), asset_volume=Decimal(1))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 4)) == 100
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 4)) == 3


def test__perform_entry_fails_before_start_date():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    with pytest.raises(ValueError, match="Cannot enter the market before the initial date."):
        portfolio._perform_entry(datetime(2019, 12, 31), currency_amount=Decimal(10), asset_volume=Decimal(1))


def test__perform_entry_fails_existing_entry_before():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    portfolio._perform_entry(datetime(2020, 1, 2), currency_amount=Decimal(10), asset_volume=Decimal(1))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 90

    with pytest.raises(ValueError, match="Cannot enter the market before an existing entry."):
        portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=Decimal(10), asset_volume=Decimal(1))


def test__perform_entry_fails_low_capital():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    with pytest.raises(ValueError, match="Not enough capital to enter the market."):
        portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=Decimal(110), asset_volume=Decimal(1))


def test__perform_exit():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    # set portfolio state at 'currency:0' and 'asset:1'
    portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=Decimal(100), asset_volume=Decimal(1))

    assert portfolio.get_available_capital_at(datetime(2020, 1, 1)) == 0
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 1)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=Decimal(1), currency_amount=Decimal(10))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 2)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 2)) == 0


def test__perform_exit_updates_following_exit():
    """Check that the following exit is updated."""
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    # set portfolio state at 'currency:0' and 'asset:2'
    portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=Decimal(100), asset_volume=Decimal(2))

    portfolio._perform_exit(datetime(2020, 1, 3), asset_volume=Decimal(1), currency_amount=Decimal(10))
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 10
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 1

    portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=Decimal(1), currency_amount=Decimal(10))

    # check the previous exit state
    assert portfolio.get_available_capital_at(datetime(2020, 1, 3)) == 20
    assert portfolio.get_asset_volume_at(datetime(2020, 1, 3)) == 0


def test__perform_exit_fails_on_volume():
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))

    # set portfolio state at 'currency:0' and 'asset:2'
    portfolio._perform_entry(datetime(2020, 1, 1), currency_amount=Decimal(100), asset_volume=Decimal(1))

    with pytest.raises(ValueError, match="Cannot exit the market, asset volume too small."):
        portfolio._perform_exit(datetime(2020, 1, 2), asset_volume=Decimal(2), currency_amount=Decimal(20))


class PortfolioUpdateFromTradeCases:
    """Generate test cases for `Portfolio.update_from_trade()`.

    The portfolio is initialized with currency at 200 and volume at 0.

    Each trade returns:
    - a trade to update the default portfolio with
    - expected wealth at different dates
    """

    def case_long_trade(self):
        fees_pct = 0.1
        money_to_invest = 50
        position = Position.open(
            open_date=datetime(2020, 1, 1),
            open_price=Decimal(10),
            money_to_invest=Decimal(money_to_invest),
            fees_pct=Decimal(str(fees_pct)),  # take 10% from 50, volume is 4.5
            side=Side.LONG,
        )
        trade = position.close(close_date=datetime(2020, 1, 3), close_price=20)
        return trade, [
            WealthItem(
                date=datetime(2020, 1, 1),
                asset=Decimal("4.5"),
                currency=Decimal(Portfolio.default_currency_amount() - money_to_invest),
            ),
            WealthItem(
                date=datetime(2020, 1, 3),
                asset=Decimal(0),
                currency=Decimal(Portfolio.default_currency_amount() + trade.total_profit),
            ),
        ]

    def case_short_trade(self):
        money_to_invest = 50
        position = Position.open(
            open_date=datetime(2020, 1, 1),
            open_price=Decimal(100),
            money_to_invest=Decimal(money_to_invest),
            fees_pct=Decimal(str(0.1)),  # take 10% from 50, volume is 0.45
            side=Side.SHORT,
        )
        trade = position.close(close_date=datetime(2020, 1, 3), close_price=110)
        return trade, [
            WealthItem(
                date=datetime(2020, 1, 1),
                asset=Decimal("0.45"),
                currency=Decimal(Portfolio.default_currency_amount() - money_to_invest),
            ),
            WealthItem(
                date=datetime(2020, 1, 3),
                asset=Decimal(0),
                currency=Decimal(Portfolio.default_currency_amount() + trade.total_profit),
            ),
        ]


@parametrize_with_cases("trade, expected_wealth_at_dates", cases=PortfolioUpdateFromTradeCases)
def test_portfolio_update_from_trade(trade: Trade, expected_wealth_at_dates: list[WealthItem]):
    portfolio = Portfolio(starting_date=datetime(2020, 1, 1))
    portfolio.update_from_trade(trade)
    for wealth_item in expected_wealth_at_dates:
        assert portfolio.get_available_capital_at(wealth_item.date) == wealth_item.currency
        assert portfolio.get_asset_volume_at(wealth_item.date) == wealth_item.asset
