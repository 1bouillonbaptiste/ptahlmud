import datetime

import pytest
from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.models.candle import Candle


@pytest.fixture
def default_parameters():
    return {
        "open": 1,
        "high": 2,
        "low": 0,
        "close": 1,
        "open_time": datetime.datetime(2020, 1, 1),
        "close_time": datetime.datetime(2020, 1, 2),
    }


def test_candle(default_parameters):
    Candle(**default_parameters)


class TestCandleFailingCases:
    """Generate failing cases for `Candle` class initialization.

    Each case returns:
    - parameters for `Candle` initialization
    - the expected error message
    """

    def case_negative_open(self, default_parameters):
        return default_parameters | {"open": -1}, "Found negative number."

    def case_negative_high(self, default_parameters):
        return default_parameters | {"high": -1}, "Found negative number."

    def case_negative_low(self, default_parameters):
        return default_parameters | {"low": -1}, "Found negative number."

    def case_negative_close(self, default_parameters):
        return default_parameters | {"close": -1}, "Found negative number."

    def case_negative_volume(self, default_parameters):
        return default_parameters | {"close": -1}, "Found negative number."

    def case_negative_total_trades(self, default_parameters):
        return default_parameters | {"close": -1}, "Found negative number."

    def case_high_lower_than_open(self, default_parameters):
        return default_parameters | {"high": 0.5}, "`high` price must be higher than `open` price."

    def case_high_lower_than_close(self, default_parameters):
        return default_parameters | {"high": 1.5, "close": 2}, "`high` price must be lower than `close` price."

    def case_low_higher_than_open(self, default_parameters):
        return default_parameters | {"low": 1.5}, "`low` price must be lower than `open` price."

    def case_low_higher_than_close(self, default_parameters):
        return default_parameters | {"low": 0.5, "close": 0.4}, "`low` price must be higher than `close` price."

    def case_high_time_lower_than_open_time(self, default_parameters):
        return default_parameters | {
            "high_time": datetime.datetime(2019, 1, 1, 1),
            "low_time": datetime.datetime(2020, 1, 1, 12),
        }, "`high_time` must be later than `open_time`."

    def case_high_time_higher_than_close_time(self, default_parameters):
        return default_parameters | {
            "high_time": datetime.datetime(2021, 1, 1, 12),
            "low_time": datetime.datetime(2020, 1, 1, 12),
        }, "`high_time` must be earlier than `close_time`."

    def case_low_time_lower_than_open_time(self, default_parameters):
        return default_parameters | {
            "high_time": datetime.datetime(2020, 1, 1, 12),
            "low_time": datetime.datetime(2019, 1, 1, 12),
        }, "`low_time` must be later than `open_time`."

    def case_low_time_higher_than_close_time(self, default_parameters):
        return default_parameters | {
            "high_time": datetime.datetime(2020, 1, 1, 12),
            "low_time": datetime.datetime(2021, 1, 1, 12),
        }, "`low_time` must be earlier than `close_time`."

    def case_high_time_set_but_low_time_not(self, default_parameters):
        return default_parameters | {
            "high_time": datetime.datetime(2020, 1, 1, 12),
        }, "`high_time` and `low_time` must be both set or both left empty."

    def case_low_time_set_but_high_time_not(self, default_parameters):
        return default_parameters | {
            "low_time": datetime.datetime(2021, 1, 1, 12)
        }, "`high_time` and `low_time` must be both set or both left empty."


@parametrize_with_cases("candle_parameters, expected_message", cases=TestCandleFailingCases)
def test_candle_fails(candle_parameters, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        Candle(**candle_parameters)
