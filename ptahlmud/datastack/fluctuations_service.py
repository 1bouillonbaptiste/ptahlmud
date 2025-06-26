"""Implement fluctuations service.

It is responsible to collect requested fluctuations.
If the data is not in the db, it will fetch it from the remote data provider.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm

from ptahlmud.datastack.clients.remote_client import RemoteClient
from ptahlmud.datastack.fluctuations import Fluctuations
from ptahlmud.datastack.fluctuations_repository import FluctuationsRepository
from ptahlmud.types import Period


@dataclass
class DateRange:
    """Store a range of dates."""

    start_date: datetime
    end_date: datetime

    def split(self, delta: timedelta) -> list["DateRange"]:
        """Split the date range into smaller chunks.

        This is an optimization, assuming the database stores daily fluctuations data.
        The date range can be split in daily chunks so that each chunk can be exactly divided by the period.
        """
        minutes_in_day = 60 * 24
        period_total_minutes = int(delta.total_seconds()) // 60
        days_per_chunk: int = math.lcm(minutes_in_day, period_total_minutes) // minutes_in_day

        chunk_size: timedelta = timedelta(days=days_per_chunk)
        chunks: list[DateRange] = []
        current_start = self.start_date
        while current_start < self.end_date:
            current_end = min(current_start + chunk_size, self.end_date)
            chunks.append(DateRange(start_date=current_start, end_date=current_end))
            current_start = current_end
        return chunks


class FluctuationsSpecs(BaseModel):
    """Specifications that fully define `Fluctuations`.

    Attributes:
        coin: the base coin of the fluctuations (e.g. 'BTC' or 'ETH')
        currency: the currency of the fluctuations (e.g. 'USD') could be another coin
        from_date: earliest open date to retrieve data
        to_date: latest close date to retrieve data
        timeframe: the time duration of each data item (e.g. '15m' or `1h`)
    """

    coin: str
    currency: str
    from_date: datetime
    to_date: datetime
    timeframe: str


class FluctuationsService:
    """Define the fluctuations service."""

    def __init__(self, repository: FluctuationsRepository, client: RemoteClient | None = None):
        self._repository = repository
        self._client = client

    def request(self, config: FluctuationsSpecs) -> Fluctuations:
        """Build fluctuations from specifications."""
        date_ranges = DateRange(start_date=config.from_date, end_date=config.to_date).split(
            delta=Period(timeframe=config.timeframe).to_timedelta()
        )
        configurations = [
            config.model_copy(update={"from_date": chunk.start_date, "to_date": chunk.end_date})
            for chunk in date_ranges
        ]

        all_fluctuations = [self._query_fluctuations(config) for config in configurations]
        return _merge_fluctuations(all_fluctuations)

    def _query_fluctuations(self, config: FluctuationsSpecs) -> Fluctuations:
        """Query the repository for a precise chunk of data."""
        chunk_fluctuations = self._repository.query(
            coin=config.coin,
            currency=config.currency,
            from_date=config.from_date,
            to_date=config.to_date,
        )
        chunk_fluctuations = _convert_fluctuations_to_period(chunk_fluctuations, period=Period(config.timeframe))
        return chunk_fluctuations

    def fetch(self, config: FluctuationsSpecs) -> None:
        """Update missing fluctuations from the database using the remote data provider."""
        if self._client is None:
            raise RuntimeError("Client is required to fetch fluctuations data.")
        incomplete_dates = self._repository.find_incomplete_dates(
            coin=config.coin,
            currency=config.currency,
            from_date=config.from_date,
            to_date=config.to_date,
        )
        for date in tqdm(incomplete_dates, desc="Downloading fluctuations data"):
            fluctuations = self._client.fetch_historical_data(
                symbol=config.coin + config.currency,
                start_date=date,
                end_date=date + timedelta(days=1),
                timeframe="1m",
            )
            self._repository.save(fluctuations, coin=config.coin, currency=config.currency)


def _build_aggregation_function() -> Callable[[pd.DataFrame], pd.Series]:
    """Create a pandas aggregation function with custom operations."""

    def custom_agg(group: pd.DataFrame) -> pd.Series:
        """Define how to aggregate a dataframe to a series."""
        if len(group) == 0:
            return pd.Series(
                {
                    "open_time": None,
                    "high_time": None,
                    "low_time": None,
                    "close_time": None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                }
            )

        high_max_idx = group["high"].idxmax()
        low_min_idx = group["low"].idxmin()

        return pd.Series(
            {
                "open_time": group["open_time"].iloc[0],
                "high_time": group["close_time"][high_max_idx],
                "low_time": group["close_time"][low_min_idx],
                "close_time": group["close_time"].iloc[-1],
                "open": group["open"].iloc[0],
                "high": group["high"].max(),
                "low": group["low"].min(),
                "close": group["close"].iloc[-1],
            }
        )

    return custom_agg


def _convert_fluctuations_to_period(fluctuations: Fluctuations, period: Period) -> Fluctuations:
    """Merge fluctuations so that each row has a period of `period`."""
    if fluctuations.size == 0:
        return fluctuations
    custom_aggregation = _build_aggregation_function()
    df = fluctuations.dataframe.copy()

    # Pandas raise a warning when the datetime is not enforced
    df["open_time"] = pd.to_datetime(df["open_time"])
    df_indexed = df.set_index("open_time", drop=False)
    df_converted = (
        df_indexed.resample(
            period.to_timedelta(),
            origin=fluctuations.earliest_open_time,
        )
        .apply(lambda group: custom_aggregation(group))
        .dropna()
        .reset_index(drop=True)
    )

    # the last candle may be incomplete when the period is not a multiple of date range
    if (df_converted.iloc[-1]["open_time"] + period.to_timedelta()) != fluctuations.dataframe.iloc[-1]["close_time"]:
        df_converted = df_converted.iloc[:-1]
    return Fluctuations(dataframe=df_converted)


def _merge_fluctuations(fluctuations_chunks: list[Fluctuations]) -> Fluctuations:
    """Concatenate fluctuations to a single dataframe."""
    if not fluctuations_chunks:
        return Fluctuations.empty()
    merged_fluctuations = (
        pd.concat([fluctuations.dataframe for fluctuations in fluctuations_chunks])
        .sort_values(by="open_time")
        .reset_index(drop=True)
    )
    return Fluctuations(dataframe=merged_fluctuations)
