import datetime

from pytest_cases import parametrize_with_cases

from ptahlmud.types.period import Period


class ToTimedeltaCases:
    """Generate cases for `Period.to_timedelta`.

    Each case returns:
    - a timeframe to initialize the period
    - the expected timedelta
    """

    def case_minute(self):
        return "1m", datetime.timedelta(minutes=1)

    def case_hour(self):
        return "2h", datetime.timedelta(hours=2)

    def case_day(self):
        return "3d", datetime.timedelta(days=3)

    def case_hour_in_minutes(self):
        return "120m", datetime.timedelta(hours=2)


@parametrize_with_cases("timeframe, expected_timedelta", cases=ToTimedeltaCases)
def test_period_to_timedelta(timeframe, expected_timedelta):
    assert Period(timeframe=timeframe).to_timedelta() == expected_timedelta
