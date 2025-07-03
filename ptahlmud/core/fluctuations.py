"""Define 'fluctuations'.

Market fluctuations are a time-series of financial candles.
A candle is a financial object that represents the price variation of any asset during a period of time.
Candles _must_ have an open, high, low and close price, an open and close time.

The `Fluctuations` class is a wrapper around a pandas DataFrame.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

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


class Fluctuations(BaseModel):
    """Interface for market fluctuations.

    Args:
        dataframe: pandas dataframe containing market data.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataframe: pd.DataFrame

    @model_validator(mode="after")
    def validate_mandatory_columns(self):
        """Check columns are present in the dataframe."""
        MANDATORY_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]
        for column in MANDATORY_COLUMNS:
            if column not in self.columns:
                raise ValueError(f"Missing column '{column}' in fluctuations.")
        return self

    @model_validator(mode="after")
    def validate_datetime_columns(self):
        """Convert `open_time` and `close_time` to `datetime` if needed."""
        self.set("open_time", pd.to_datetime(self.get("open_time")))
        self.set("close_time", pd.to_datetime(self.get("close_time")))
        return self

    @model_validator(mode="after")
    def validate_rows_order(self):
        """Sort dataframe rows by their `open_time`."""
        self.dataframe.sort_values(by="open_time", ascending=True).drop_duplicates(subset=["open_time"]).reset_index(
            drop=True
        )
        return self

    @classmethod
    def from_pandas(cls, dataframe: pd.DataFrame) -> "Fluctuations":
        """Create a fluctuations instance from a pandas DataFrame."""
        return cls(dataframe=dataframe)

    @classmethod
    def empty(cls) -> "Fluctuations":
        """Generate an empty fluctuations instance."""
        return cls(dataframe=pd.DataFrame(columns=MANDATORY_COLUMNS))

    @property
    def size(self) -> int:
        """Return the total number of candles."""
        return len(self.dataframe)

    @cached_property
    def columns(self):
        """Return the columns of the underlying pandas DataFrame."""
        return self.dataframe.columns

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

    def get(self, name: str) -> pd.Series:
        """Return a column of the underlying pandas DataFrame."""
        return self.dataframe[name]

    def set(self, name: str, series: pd.Series) -> None:
        """Insert a column in the underlying pandas DataFrame."""
        self.dataframe[name] = series

    def subset(self, from_date: datetime | None = None, to_date: datetime | None = None) -> "Fluctuations":
        """Select the candles between the given dates as a new instance of `Fluctuations`."""
        return Fluctuations(
            dataframe=self.dataframe[
                (self.get("open_time") >= (from_date or self.earliest_open_time))
                & (self.get("open_time") < (to_date or self.latest_close_time))
            ]
        )

    def get_candle_at(self, date: datetime) -> Candle:
        """Return the candle containing `date`."""
        if date > self.latest_close_time:
            raise ValueError("Date is after the latest close time.")
        row = self.dataframe[self.dataframe["open_time"] >= date].iloc[0]
        return Candle.from_series(row)

    def last_candle(self) -> Candle:
        """Return the last candle."""
        return Candle.from_series(self.dataframe.iloc[-1])

    def iter_candles(self) -> Iterable[Candle]:
        """Iterate over the candles in the fluctuations."""
        for _, row in self.dataframe.iterrows():
            yield Candle.from_series(row)
