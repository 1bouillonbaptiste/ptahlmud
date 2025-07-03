"""Define fluctuations concept.

The `Fluctuations` class is a wrapper above a pandas dataframe for market data manipulation.
"""

from datetime import datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from ptahlmud.types import Period


class Fluctuations(BaseModel):
    """Interface for market fluctuations.

    Attributes:
        dataframe: pandas dataframe containing market data.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataframe: pd.DataFrame

    @model_validator(mode="after")
    def validate_mandatory_columns(self):
        """Check columns are present in the dataframe."""
        MANDATORY_COLUMNS = ["open_time", "close_time", "open", "high", "low", "close"]
        for column in MANDATORY_COLUMNS:
            if column not in self.dataframe.columns:
                raise ValueError(f"Missing column '{column}' in fluctuations.")
        return self

    @model_validator(mode="after")
    def validate_datetime_columns(self):
        """Convert `open_time` and `close_time` to `datetime` if needed."""
        self.dataframe.loc[:, "open_time"] = pd.to_datetime(self.dataframe["open_time"])
        self.dataframe.loc[:, "close_time"] = pd.to_datetime(self.dataframe["close_time"])

        return self

    @model_validator(mode="after")
    def validate_rows_order(self):
        """Sort dataframe rows by their `open_time`."""
        self.dataframe.sort_values(by="open_time", ascending=True).drop_duplicates(subset=["open_time"]).reset_index(
            drop=True
        )
        return self

    @classmethod
    def empty(cls) -> "Fluctuations":
        """Create an empty fluctuations."""
        empty_dataframe = pd.DataFrame(columns=["open_time", "close_time", "open", "high", "low", "close"])
        return cls(dataframe=empty_dataframe)

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
        """Get the duration in minutes of fluctuations items."""
        first_candle = self.dataframe.iloc[0]
        minutes = int((first_candle["close_time"] - first_candle["open_time"]).total_seconds()) // 60
        timeframe = str(minutes) + "m"
        return Period(timeframe)

    def subset(self, from_date: datetime, to_date: datetime) -> "Fluctuations":
        """Create a new instance from rows within a specified date range."""
        return Fluctuations(
            dataframe=self.dataframe[
                (self.dataframe["open_time"] >= from_date) & (self.dataframe["open_time"] < to_date)
            ]
        )
