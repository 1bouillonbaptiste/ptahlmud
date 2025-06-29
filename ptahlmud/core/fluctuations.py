"""Define 'fluctuations'.

Market fluctuations are a time-series of financial candles.
A candle is a financial object that represents the price variation of any asset during a period of time.
Candles _must_ have an open, high, low and close price, an open and close time.

The `Fluctuations` class is a wrapper around a pandas DataFrame.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from ptahlmud.core.period import Period

MANDATORY_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]


class Fluctuations:
    """Interface for market fluctuations.

    Args:
        dataframe: pandas dataframe containing market data.
    """

    def __init__(self, dataframe: pd.DataFrame):
        """Load fluctuations from a pandas DataFrame."""
        for column in MANDATORY_COLUMNS:
            if column not in dataframe.columns:
                raise ValueError(f"Missing column '{column}' in fluctuations.")

        dataframe.loc[:, "open_time"] = pd.to_datetime(dataframe["open_time"])
        dataframe.loc[:, "close_time"] = pd.to_datetime(dataframe["close_time"])

        dataframe.sort_values(by="open_time", ascending=True).drop_duplicates(subset=["open_time"]).reset_index(
            drop=True
        )

        self.dataframe = dataframe

    @classmethod
    def empty(cls) -> "Fluctuations":
        """Generate an empty fluctuations instance."""
        return cls(dataframe=pd.DataFrame(columns=MANDATORY_COLUMNS))

    @property
    def size(self) -> int:
        """Return the total number of candles."""
        return len(self.dataframe)

    @property
    def earliest_open_time(self) -> datetime:
        """Return the earliest open time."""
        first_candle = self.dataframe.iloc[0]
        return first_candle["open_time"].to_pydatetime()

    @property
    def latest_close_time(self) -> datetime:
        """Return the latest close time."""
        last_candle = self.dataframe.iloc[-1]
        return last_candle["close_time"].to_pydatetime()

    @property
    def period(self) -> Period:
        """The time duration of the fluctuations as a `Period` object, assume every candle shares the same period."""
        first_candle = self.dataframe.iloc[0]
        candle_total_minutes = int((first_candle["close_time"] - first_candle["open_time"]).total_seconds()) // 60
        return Period(timeframe=str(candle_total_minutes) + "m")

    def subset(self, from_date: datetime | None = None, to_date: datetime | None = None) -> "Fluctuations":
        """Select the candles between the given dates as a new instance of `Fluctuations`."""
        return Fluctuations(
            dataframe=self.dataframe[
                (self.dataframe["open_time"] >= (from_date or self.earliest_open_time))
                & (self.dataframe["open_time"] < (to_date or self.latest_close_time))
            ]
        )

    def first_candles(self, n: int) -> "Fluctuations":
        """Return the first `n` candles as a new instance of `Fluctuations`."""
        if n > self.size:
            raise ValueError("Number of candles to subset is greater than the number of available candles.")
        return Fluctuations(dataframe=self.dataframe.iloc[:n])


@dataclass(slots=True, frozen=True)
class Candle:
    """Represent a candle.

    Since we instantiate potentially billions of candles, we require a lightweight object.
    We don't use pydantic model for performance reason.
    We don't use a NamedTuple because we need to access candle's attributes frequently.

    Attributes:
        open: price the candle opened at.
        high: price the candle reached at its highest point.
        low: price the candle reached at its lowest point.
        close: price the candle closed at.
        open_time: time the candle opened.
        close_time: time the candle closed.
        high_time: time the candle reached its highest point.
        low_time: time the candle reached its lowest point.

    """

    open: float
    high: float
    low: float
    close: float

    open_time: datetime
    close_time: datetime

    high_time: datetime | None = None
    low_time: datetime | None = None
