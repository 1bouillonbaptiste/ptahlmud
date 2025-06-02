from datetime import datetime

import pytest
from pytest_cases import parametrize_with_cases

from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.testing.generate import generate_candles
from ptahlmud.types.period import Period


@pytest.fixture()
def random_fluctuations():
    period = Period(timeframe="5m")
    candles = generate_candles(from_date=datetime(2020, 1, 1), to_date=datetime(2020, 1, 1, hour=1), period=period)
    return Fluctuations(candles=candles, period=period)


class FluctuationsSubsetCases:
    """Generate cases for `Fluctuations.subset()`.

    Each case returns:
    - the date from which to start the subset
    - the date until which to end the subset
    - the expected start date
    - the expected end date
    """

    def case_none(self):
        return None, None, datetime(2020, 1, 1), datetime(2020, 1, 1, hour=1)

    def case_from_date_equal_open_time(self):
        return datetime(2020, 1, 1, minute=5), None, datetime(2020, 1, 1, minute=5), datetime(2020, 1, 1, hour=1)

    def case_from_date(self):
        return datetime(2020, 1, 1, minute=3), None, datetime(2020, 1, 1), datetime(2020, 1, 1, hour=1)

    def case_to_date_equal_close_time(self):
        return None, datetime(2020, 1, 1, minute=55), datetime(2020, 1, 1), datetime(2020, 1, 1, minute=55)

    def case_to_date(self):
        return None, datetime(2020, 1, 1, minute=57), datetime(2020, 1, 1), datetime(2020, 1, 1, hour=1)


@parametrize_with_cases("from_date, to_date, expected_from_date, expected_to_date", cases=FluctuationsSubsetCases)
def test_subset(from_date, to_date, expected_from_date, expected_to_date, random_fluctuations):
    fluctuations_subset: Fluctuations = random_fluctuations.subset(from_date=from_date, to_date=to_date)

    assert fluctuations_subset.candles[0].open_time == expected_from_date
    assert fluctuations_subset.candles[-1].close_time == expected_to_date
