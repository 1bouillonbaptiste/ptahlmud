"""Define `Period` type.

Financial time series are either by **tick** or **time-based***.
Tick data records every transaction that occurs in the market,
while time-based data records the price at a specific time interval with a given period.

`Period` supports 'minutes', 'hours' and 'days' time frames, and the lowest supported time frame is 1-minute.
"""

import datetime
import re


class Period:
    """Represent a period.

    Arg:
        timeframe: a string containing a time unit and duration of the period (e.g. "1m" or "1d")
    """

    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self._unit, self._value = _parse_timeframe(timeframe)

    def __post_init__(self):
        """Validate the period attributes."""
        if self._unit not in ["m", "h", "d"]:
            raise ValueError(f"Unknown period unit `{self._unit}`. Supported units are: 'm', 'h' and 'd'.")
        if self._value < 1:
            raise ValueError("Period value must be a strictly positive integer.")

    def to_timedelta(self):
        """Convert the period to a `datetime.timedelta` object."""
        units_adapter = {"m": "minutes", "h": "hours", "d": "days"}
        return datetime.timedelta(**{units_adapter[self._unit]: self._value})


def _parse_timeframe(timeframe: str) -> tuple[str, int]:
    """Parse a timeframe to retrieve its time unit and value."""
    # a valid timeframe has the following format: "[value][unit]"
    if not re.match(r"^\d+[a-z]$", timeframe):
        raise ValueError("Invalid timeframe.")
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    return unit, value
