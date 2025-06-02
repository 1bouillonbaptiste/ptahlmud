"""Helper to generate random entities."""

from datetime import datetime

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
    volumes = (np.random.beta(a=2, b=2, size=size) / 2 + 0.25) * 1000
    open_dates = [initial_open_time + ii * period.to_timedelta() for ii in range(size)]
    close_dates = [open_date + period.to_timedelta() for open_date in open_dates]

    candles: list[Candle] = [
        Candle(
            open=round(float(open_price), 3),
            high=round(float(high_price), 3),
            low=round(float(low_price), 3),
            close=round(float(close_price), 3),
            volume=round(float(volume), 3),
            total_trades=1,
            open_time=open_time,
            close_time=close_time,
            high_time=None,
            low_time=None,
        )
        for open_price, high_price, low_price, close_price, volume, open_time, close_time in zip(
            opens, highs, lows, closes, volumes, open_dates, close_dates, strict=False
        )
    ]
    return candles
