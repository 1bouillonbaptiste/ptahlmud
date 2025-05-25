"""Helper to generate random entities."""

from datetime import datetime, timedelta

import numpy as np

from ptahlmud.types.candle import Candle
from ptahlmud.types.period import Period


def generate_candles(
    size: int = 1000,
    period: Period | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[Candle]:
    """Generate random plausible candles.

    Args:
        size: number of candles to generate
        period: the time duration of each candle
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
        last_close_time = from_date + period.to_timedelta() * size

    size = int((last_close_time - initial_open_time) / period.to_timedelta())
    close_price: float = 1000
    candles = []
    for ii in range(size):
        open_price = close_price
        close_price = open_price * (1 + np.random.normal(scale=0.01))
        high_price = np.max([open_price, close_price]) * (1 + np.random.beta(a=2, b=5) / 100)
        low_price = np.min([open_price, close_price]) * (1 - np.random.beta(a=2, b=5) / 100)
        volume = (np.random.beta(a=2, b=2) / 2 + 0.25) * 1000
        candles.append(
            Candle(
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                total_trades=1,
                open_time=initial_open_time + ii * period.to_timedelta(),
                close_time=initial_open_time + (ii + 1) * period.to_timedelta() - timedelta(milliseconds=90),
                high_time=None,
                low_time=None,
            )
        )
    return candles
