"""Define 'fluctuations'.

Market fluctuations are a time-series of financial candles.
A candle is a financial object that represents the price variation of any asset during a period of time.
Candles _must_ have an open, high, low and close price, an open and close time.

The `Fluctuations` class is also a wrapper around a pandas DataFrame.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

import pandas as pd

from ptahlmud.core.period import Period

MANDATORY_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]


@dataclass(slots=True, frozen=True)
class Candle:
    """Represent a candle.

    Since we instantiate potentially billions of candles, we require a lightweight object.
    We don't use pydantic model for performance reasons.
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

    @classmethod
    def from_series(cls, series: pd.Series) -> "Candle":
        """Create a candle from a pandas Series."""
        row_values = {column: series[column] for column in MANDATORY_COLUMNS} | {
            "high_time": series.get("high_time"),
            "low_time": series.get("low_time"),
        }
        return cls(**row_values)


def _validate_mandatory_columns(dataframe: pd.DataFrame) -> None:
    """Check columns are present in the dataframe."""
    missing_columns = set(MANDATORY_COLUMNS) - set(dataframe.columns)
    if missing_columns:
        columns_str = "', '".join(missing_columns)
        raise ValueError(f"Missing mandatory columns column(s): '{columns_str}'.")


class Fluctuations:
    """Interface for market fluctuations.

    Attributes:
        _dataframe: pandas dataframe containing market data.
    """

    _dataframe: pd.DataFrame

    def __init__(self, dataframe: pd.DataFrame):
        _validate_mandatory_columns(dataframe)

        dataframe = (
            dataframe.sort_values(by="open_time", ascending=True)
            .drop_duplicates(subset=["open_time"])
            .reset_index(drop=True)
        )

        self._dataframe = dataframe

        self.set("open_time", pd.to_datetime(self.get("open_time")))
        self.set("close_time", pd.to_datetime(self.get("close_time")))

    @classmethod
    def empty(cls) -> "Fluctuations":
        """Generate an empty fluctuations instance."""
        return cls(dataframe=pd.DataFrame(columns=MANDATORY_COLUMNS))

    @property
    def dataframe(self):
        """Return the underlying pandas DataFrame."""
        return self._dataframe.copy()

    @property
    def size(self) -> int:
        """Return the total number of candles."""
        return len(self._dataframe)

    @cached_property
    def columns(self):
        """Return the columns of the underlying pandas DataFrame."""
        return self._dataframe.columns

    @property
    def earliest_open_time(self) -> datetime:
        """Return the earliest open time."""
        first_candle = Candle.from_series(self._dataframe.iloc[0])
        return first_candle.open_time

    @property
    def latest_close_time(self) -> datetime:
        """Return the latest close time."""
        last_candle = Candle.from_series(self._dataframe.iloc[-1])
        return last_candle.close_time

    @property
    def period(self) -> Period:
        """The time duration of the fluctuations as a `Period` object, assume every candle shares the same period."""
        first_candle = self._dataframe.iloc[0]
        candle_total_minutes = int((first_candle["close_time"] - first_candle["open_time"]).total_seconds()) // 60
        return Period(timeframe=str(candle_total_minutes) + "m")

    def get(self, name: str) -> pd.Series:
        """Return a column of the underlying pandas DataFrame."""
        return self._dataframe[name]

    def set(self, name: str, series: pd.Series) -> None:
        """Insert a column in the underlying pandas DataFrame."""
        self._dataframe[name] = series

    def subset(self, from_date: datetime | None = None, to_date: datetime | None = None) -> "Fluctuations":
        """Select the candles between the given dates as a new instance of `Fluctuations`."""
        return Fluctuations(
            dataframe=self._dataframe[
                (self.get("open_time") >= (from_date or self.earliest_open_time))
                & (self.get("open_time") < (to_date or self.latest_close_time))
            ]
        )

    def get_candle_at(self, date: datetime) -> Candle:
        """Return the candle containing `date`."""
        if date > self.latest_close_time:
            raise ValueError("Date is after the latest close time.")
        row = self._dataframe[self._dataframe["open_time"] >= date].iloc[0]
        return Candle.from_series(row)

    def last_candle(self) -> Candle:
        """Return the last candle."""
        return Candle.from_series(self._dataframe.iloc[-1])

    def iter_candles(self) -> Iterable[Candle]:
        """Iterate over the candles in the fluctuations."""
        for _, row in self._dataframe.iterrows():
            yield Candle.from_series(row)
