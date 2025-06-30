from datetime import datetime

import numpy as np
import pandas as pd

from ptahlmud.core import Period
from ptahlmud.core.fluctuations import Fluctuations


def generate_fluctuations(
    size: int = 1000,
    period: Period | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Fluctuations:
    """Generate randomized fluctuations.

    Args:
        size: number of candles to generate
        period: the time duration of each data item
        from_date: earliest open date
        to_date: latest close date

    Returns:
        randomly generated candles as a list
    """
    if period is None:
        period = Period(timeframe="1m")

    initial_open_time: datetime = from_date or datetime(2020, 1, 1)
    last_close_time: datetime = to_date or initial_open_time + period.to_timedelta() * size

    if from_date is None:
        initial_open_time = last_close_time - period.to_timedelta() * size
    if to_date is None:
        last_close_time = initial_open_time + period.to_timedelta() * size

    size = int((last_close_time - initial_open_time) / period.to_timedelta())

    candles_returns = np.random.normal(scale=0.01, size=size)
    high_diffs = np.random.beta(a=2, b=5, size=size) / 100
    low_diffs = np.random.beta(a=2, b=5, size=size) / 100

    initial_close: float = 1000
    closes = np.cumprod(1 + candles_returns) * initial_close
    opens = np.array([initial_close, *closes[:-1].tolist()])
    highs = (1 + high_diffs) * np.max([closes, opens], axis=0)
    lows = (1 - low_diffs) * np.min([closes, opens], axis=0)
    open_dates = [initial_open_time + ii * period.to_timedelta() for ii in range(size)]
    close_dates = [open_date + period.to_timedelta() for open_date in open_dates]

    candles = {
        "open_time": open_dates,
        "close_time": close_dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
    }
    dataframe = pd.DataFrame(candles)
    return Fluctuations(dataframe=dataframe)
